"""Structured-output adapter for job discovery and extraction."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import replace
from typing import List, Optional, Sequence

from openai import AsyncOpenAI

from app.career.models import (
    ApplicantCompanyAssessment,
    CareerRoadmapDraft,
    ExtractedJob,
    ExtractedJobBatch,
    JobDiscoveryPlan,
    VerifiedJobPage,
)
from app.config.resources import read_text
from app.schemas.career import (
    CareerRoadmapRequest,
    CompanyRecommendationRequest,
    JobRecommendation,
    JobRecommendationRequest,
    RequirementGap,
    RequirementInsight,
)
from app.service.openai_chat_client import (
    OPENAI_FAST,
    OPENAI_REASONING,
    create_openai_client,
    parse_structured,
)

logger = logging.getLogger(__name__)

_PLAN_OPTIONS = replace(OPENAI_FAST, max_tokens=2048)
_EXTRACTION_OPTIONS = replace(OPENAI_FAST, max_tokens=8192)
_ROADMAP_OPTIONS = replace(OPENAI_REASONING, max_tokens=8192)
_COMPANY_ASSESSMENT_OPTIONS = replace(OPENAI_REASONING, max_tokens=4096)


class CareerLlmClient:
    def __init__(self, client: Optional[AsyncOpenAI] = None) -> None:
        self._owns_client = client is None
        self._client = client or create_openai_client()

    async def plan_discovery(
        self, request: JobRecommendationRequest
    ) -> JobDiscoveryPlan:
        prompt = read_text("prompts", "career", "job_discovery.txt")
        profile = request.profile.model_dump(
            mode="json", exclude={"user_id", "resume_text"}
        )
        payload = {
            "profile": profile,
            "requested_target_roles": request.target_roles,
            "target_companies": request.target_companies,
            "locations": request.locations,
            "employment_types": request.employment_types,
        }
        return await parse_structured(
            self._client,
            prompt,
            json.dumps(payload, ensure_ascii=False),
            JobDiscoveryPlan,
            options=_PLAN_OPTIONS,
        )

    async def assess_company_candidate(
        self, request: CompanyRecommendationRequest
    ) -> ApplicantCompanyAssessment:
        prompt = read_text("prompts", "career", "company_assessment.txt")
        business_rubric = read_text("track", "business.txt")
        engineering_rubric = read_text("track", "engineering.txt")
        profile = request.profile.model_dump(
            mode="json", exclude={"user_id", "resume_text"}
        )
        payload = {
            "profile": profile,
            "requested_target_roles": request.target_roles,
            "self_introduction": [
                {"question": question, "answer": answer}
                for question, answer in zip(
                    request.question_list, request.answer_list, strict=True
                )
            ],
        }
        system_prompt = (
            f"{prompt}\n\n<business_track_rubric>\n{business_rubric}"
            f"\n</business_track_rubric>\n\n<engineering_track_rubric>\n"
            f"{engineering_rubric}\n</engineering_track_rubric>"
        )
        return await parse_structured(
            self._client,
            system_prompt,
            json.dumps(payload, ensure_ascii=False),
            ApplicantCompanyAssessment,
            options=_COMPANY_ASSESSMENT_OPTIONS,
        )

    async def extract_jobs(
        self, pages: Sequence[VerifiedJobPage]
    ) -> List[ExtractedJob]:
        prompt = read_text("prompts", "career", "extract_jobs.txt")
        batches = [pages[start : start + 5] for start in range(0, len(pages), 5)]
        semaphore = asyncio.Semaphore(2)

        async def extract_batch(
            batch: Sequence[VerifiedJobPage],
        ) -> List[ExtractedJob]:
            payload = {
                "candidates": [
                    {
                        "candidate_id": page.candidate_id,
                        "search_title": page.hit.title,
                        "snippet": page.hit.content[:2_000],
                        "candidate_text": page.page_text[:10_000],
                    }
                    for page in batch
                ]
            }
            async with semaphore:
                try:
                    result = await parse_structured(
                        self._client,
                        prompt,
                        json.dumps(payload, ensure_ascii=False),
                        ExtractedJobBatch,
                        options=_EXTRACTION_OPTIONS,
                    )
                except Exception as exc:  # noqa: BLE001 - preserve other chunks
                    logger.warning(
                        "Job extraction chunk failed: size=%s error_type=%s",
                        len(batch),
                        type(exc).__name__,
                    )
                    return []
                valid_ids = {page.candidate_id for page in batch}
                return [
                    posting
                    for posting in result.postings
                    if posting.candidate_id in valid_ids
                ]

        results = await asyncio.gather(*(extract_batch(batch) for batch in batches))
        return [posting for batch in results for posting in batch]

    async def build_roadmap(
        self,
        request: CareerRoadmapRequest,
        required: Sequence[RequirementInsight],
        preferred: Sequence[RequirementInsight],
        gaps: Sequence[RequirementGap],
        jobs: Sequence[JobRecommendation],
    ) -> CareerRoadmapDraft:
        prompt = read_text("prompts", "career", "roadmap.txt")
        payload = {
            "profile": request.profile.model_dump(
                mode="json", exclude={"user_id", "resume_text"}
            ),
            "target_role": request.target_role,
            "target_company": request.target_company,
            "common_required_requirements": [
                item.model_dump(mode="json") for item in required
            ],
            "common_preferred_requirements": [
                item.model_dump(mode="json") for item in preferred
            ],
            "priority_gaps": [item.model_dump(mode="json") for item in gaps],
            "reference_jobs": [
                {
                    "company": job.company,
                    "title": job.title,
                    "required_requirements": job.required_requirements,
                    "preferred_requirements": job.preferred_requirements,
                }
                for job in jobs
            ],
        }
        return await parse_structured(
            self._client,
            prompt,
            json.dumps(payload, ensure_ascii=False),
            CareerRoadmapDraft,
            options=_ROADMAP_OPTIONS,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.close()
