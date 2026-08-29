"""Career recommendation orchestration."""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone
from typing import Dict, Iterable, List, Literal, Sequence

from app.career.errors import CareerConfigurationError
from app.career.llm_client import CareerLlmClient
from app.career.company_ranking import (
    build_company_recommendation,
    company_candidate_priority,
)
from app.career.models import (
    CareerRoadmapDraft,
    JobDiscoveryPlan,
    JobSearchHit,
    VerifiedJobPage,
)
from app.career.page_verifier import JobPageVerifier, canonical_url
from app.career.ranking import (
    compact,
    company_matches,
    deadline_is_past,
    ground_extraction,
    profile_matches_requirement,
    rank_job,
)
from app.career.search_client import TavilyJobSearchClient
from app.repository.previous_resume_data_repository import PreviousResumeDataRepository
from app.schemas.career import (
    ApplicantAxisScores,
    CareerMilestone,
    CareerProfileDto,
    CareerRoadmapRequest,
    CareerRoadmapResponse,
    CompanyRecommendationRequest,
    CompanyRecommendationResponse,
    JobRecommendation,
    JobRecommendationRequest,
    JobRecommendationResponse,
    RequirementGap,
    RequirementInsight,
    RoleRecommendation,
)

logger = logging.getLogger(__name__)

_ROLE_KEYWORDS: Dict[str, Sequence[str]] = {
    "백엔드 개발자": ("python", "fastapi", "spring", "java", "kafka", "backend", "api"),
    "데이터 엔지니어": ("sql", "spark", "airflow", "etl", "warehouse", "데이터 파이프라인"),
    "AI/ML 엔지니어": ("pytorch", "tensorflow", "머신러닝", "machine learning", "llm", "모델"),
    "클라우드/DevOps 엔지니어": ("aws", "kubernetes", "docker", "terraform", "devops", "ci/cd"),
    "프론트엔드 개발자": ("react", "vue", "typescript", "javascript", "frontend"),
}


class CareerRecommendationService:
    def __init__(
        self,
        llm_client: CareerLlmClient | None = None,
        search_client: TavilyJobSearchClient | None = None,
        page_verifier: JobPageVerifier | None = None,
        previous_resume_data_repository: PreviousResumeDataRepository | None = None,
    ) -> None:
        self._llm = llm_client or CareerLlmClient()
        self._search = search_client or TavilyJobSearchClient()
        self._verifier = page_verifier or JobPageVerifier()
        self._history = previous_resume_data_repository

    async def recommend(
        self, request: JobRecommendationRequest
    ) -> JobRecommendationResponse:
        generated_at = datetime.now(timezone.utc)
        roles, queries = await self._discovery_plan(request)
        raw_hits = await self._search_all(queries)
        hits = _deduplicate_hits(raw_hits)[: request.candidate_limit]
        verified_pages = _deduplicate_verified_pages(await self._verify_all(hits))
        active_pages = [
            page
            for page in verified_pages
            if page.verification_status == "verified_active"
        ]

        extracted = await self._llm.extract_jobs(active_pages) if active_pages else []
        extracted_by_id = {posting.candidate_id: posting for posting in extracted}
        checked_at = datetime.now(timezone.utc)
        recommendations = []
        for page in active_pages:
            posting = extracted_by_id.get(page.candidate_id)
            if posting is None:
                continue
            posting = ground_extraction(posting, page)
            if deadline_is_past(posting.deadline):
                continue
            if request.target_companies and not company_matches(
                posting.company, request.target_companies
            ):
                continue
            recommendations.append(
                rank_job(
                    posting,
                    page,
                    request.profile,
                    roles,
                    request.locations,
                    checked_at,
                )
            )

        recommendations.sort(
            key=lambda job: (job.fit_score, job.deadline or ""), reverse=True
        )
        selected = recommendations[: request.result_limit]
        notice = None
        if len(selected) < request.result_limit:
            notice = (
                f"현재 시점에 링크 검증과 공고 추출을 통과한 결과가 {len(selected)}개입니다. "
                "종료되거나 상태를 확인할 수 없는 공고는 포함하지 않았습니다."
            )
        return JobRecommendationResponse(
            generated_at=generated_at,
            resolved_target_roles=roles,
            search_queries=queries,
            searched_candidate_count=len(hits),
            verified_candidate_count=len(active_pages),
            jobs=selected,
            notice=notice,
        )

    async def recommend_companies(
        self, request: CompanyRecommendationRequest
    ) -> CompanyRecommendationResponse:
        if self._history is None:
            raise CareerConfigurationError(
                "기업 추천용 과거 합격 사례 저장소가 구성되지 않았습니다."
            )

        assessment = await self._llm.assess_company_candidate(request)
        roles = [item.role for item in assessment.role_recommendations]
        applicant_scores = ApplicantAxisScores(
            x=assessment.x.score,
            y=assessment.y.score,
            z=assessment.z.score,
        )
        stats = await self._history.list_company_track_stats(
            assessment.track.value, request.minimum_sample_count
        )
        candidates = sorted(
            stats,
            key=lambda item: company_candidate_priority(assessment, item),
            reverse=True,
        )[: request.company_candidate_limit]
        role_recommendations = [
            RoleRecommendation(role=item.role, evidence=item.evidence)
            for item in assessment.role_recommendations
        ]
        methodology_notice = (
            "이 결과는 합격 확률이 아니라, 과거 합격 사례의 X/Y/Z 평균과 현재 활성 공고 요건을 "
            "비교한 적합도입니다. 불합격 사례가 없어 실제 합격률로 해석할 수 없습니다."
        )
        if not candidates:
            return CompanyRecommendationResponse(
                generated_at=datetime.now(timezone.utc),
                resolved_track=assessment.track.value,
                resolved_target_roles=roles,
                role_recommendations=role_recommendations,
                applicant_scores=applicant_scores,
                considered_company_count=0,
                verified_company_count=0,
                companies=[],
                methodology_notice=methodology_notice,
                notice=(
                    f"동일 직군에서 최소 {request.minimum_sample_count}건의 합격 사례 표본을 "
                    "충족한 기업이 없습니다."
                ),
            )

        primary_role = roles[0]
        queries = [
            f"{item.company} 공식 채용 {primary_role}"
            for item in candidates
        ]
        raw_hits = await self._search_all(queries)
        hits = _deduplicate_hits(raw_hits)[: request.company_candidate_limit * 5]
        verified_pages = _deduplicate_verified_pages(await self._verify_all(hits))
        active_pages = [
            page
            for page in verified_pages
            if page.verification_status == "verified_active"
        ]
        extracted = await self._llm.extract_jobs(active_pages) if active_pages else []
        extracted_by_id = {posting.candidate_id: posting for posting in extracted}
        checked_at = datetime.now(timezone.utc)

        recommendations = []
        for stats_item in candidates:
            matching_jobs = []
            for page in active_pages:
                posting = extracted_by_id.get(page.candidate_id)
                if posting is None or not company_matches(
                    posting.company, [stats_item.company]
                ):
                    continue
                posting = ground_extraction(posting, page)
                if deadline_is_past(posting.deadline):
                    continue
                matching_jobs.append(
                    rank_job(
                        posting,
                        page,
                        request.profile,
                        roles,
                        request.locations,
                        checked_at,
                    )
                )
            if not matching_jobs:
                continue
            best_job = max(
                matching_jobs,
                key=lambda job: (job.fit_score, job.deadline or ""),
            )
            recommendations.append(
                build_company_recommendation(
                    assessment,
                    stats_item,
                    best_job,
                    primary_role,
                )
            )

        recommendations.sort(
            key=lambda item: (
                item.fit_score,
                item.historical_sample_count,
                item.active_job.deadline or "",
            ),
            reverse=True,
        )
        selected = recommendations[: request.result_limit]
        notice = None
        if len(selected) < request.result_limit:
            notice = (
                f"과거 합격 사례 기준과 현재 활성 공고 검증을 모두 통과한 기업이 "
                f"{len(selected)}곳입니다."
            )
        return CompanyRecommendationResponse(
            generated_at=datetime.now(timezone.utc),
            resolved_track=assessment.track.value,
            resolved_target_roles=roles,
            role_recommendations=role_recommendations,
            applicant_scores=applicant_scores,
            considered_company_count=len(candidates),
            verified_company_count=len(recommendations),
            companies=selected,
            methodology_notice=methodology_notice,
            notice=notice,
        )

    async def roadmap(self, request: CareerRoadmapRequest) -> CareerRoadmapResponse:
        recommendation_request = JobRecommendationRequest(
            profile=request.profile,
            target_roles=[request.target_role],
            target_companies=[request.target_company] if request.target_company else [],
            locations=request.locations,
            employment_types=request.employment_types,
            candidate_limit=request.candidate_limit,
            result_limit=3,
        )
        recommendation_result = await self.recommend(recommendation_request)
        required = _aggregate_requirements(
            recommendation_result.jobs, "required_requirements", "required"
        )
        preferred = _aggregate_requirements(
            recommendation_result.jobs, "preferred_requirements", "preferred"
        )
        gaps = _find_priority_gaps(required, preferred, request.profile)
        try:
            draft = await self._llm.build_roadmap(
                request,
                required,
                preferred,
                gaps,
                recommendation_result.jobs,
            )
        except Exception as exc:  # noqa: BLE001 - deterministic fallback is intentional
            logger.warning(
                "Career roadmap generation failed; using deterministic fallback: %s",
                type(exc).__name__,
            )
            draft = _fallback_roadmap(request, gaps)

        notice = recommendation_result.notice
        if not recommendation_result.jobs:
            notice = (
                "검증된 참고 공고가 없어 입력된 이력과 목표 직무만으로 로드맵을 작성했습니다. "
                "공고 기반 요건은 검색 결과가 확보되면 다시 확인해야 합니다."
            )
        return CareerRoadmapResponse(
            generated_at=datetime.now(timezone.utc),
            target_role=request.target_role,
            target_company=request.target_company,
            current_fit_summary=draft.current_fit_summary,
            common_required_requirements=required,
            common_preferred_requirements=preferred,
            priority_gaps=gaps,
            milestones=[
                CareerMilestone(
                    horizon=item.horizon,
                    objective=item.objective,
                    actions=item.actions,
                    completion_criteria=item.completion_criteria,
                )
                for item in draft.milestones
            ],
            reference_jobs=recommendation_result.jobs,
            notice=notice,
        )

    async def _discovery_plan(
        self, request: JobRecommendationRequest
    ) -> tuple[List[str], List[str]]:
        try:
            plan = await self._llm.plan_discovery(request)
        except Exception as exc:  # noqa: BLE001 - deterministic fallback is intentional
            logger.warning(
                "Job discovery planning failed; using deterministic fallback: %s",
                type(exc).__name__,
            )
            plan = JobDiscoveryPlan(
                target_roles=request.target_roles or _infer_roles(request.profile),
                queries=_fallback_queries(
                    request.target_roles or _infer_roles(request.profile), request
                ),
            )
        roles = request.target_roles or plan.target_roles
        roles = list(dict.fromkeys(roles))[:3]
        queries = _complete_queries(plan.queries, roles, request)
        return roles, queries

    async def _search_all(self, queries: Sequence[str]) -> List[JobSearchHit]:
        semaphore = asyncio.Semaphore(4)

        async def search_one(query: str) -> List[JobSearchHit]:
            async with semaphore:
                try:
                    return await self._search.search(query, max_results=5)
                except CareerConfigurationError:
                    raise
                except Exception as exc:  # noqa: BLE001 - preserve partial results
                    logger.warning(
                        "Job search failed: query_hash=%s error_type=%s",
                        hash(query),
                        type(exc).__name__,
                    )
                    return []

        batches = await asyncio.gather(*(search_one(query) for query in queries))
        return [hit for batch in batches for hit in batch]

    async def _verify_all(
        self, hits: Sequence[JobSearchHit]
    ) -> List[VerifiedJobPage]:
        semaphore = asyncio.Semaphore(6)

        async def verify_one(index: int, hit: JobSearchHit) -> VerifiedJobPage:
            async with semaphore:
                return await self._verifier.verify(hit, f"job-{index + 1:03d}")

        return list(
            await asyncio.gather(
                *(verify_one(index, hit) for index, hit in enumerate(hits))
            )
        )

    async def aclose(self) -> None:
        await self._llm.aclose()
        await self._search.aclose()
        await self._verifier.aclose()


def _infer_roles(profile: CareerProfileDto) -> List[str]:
    text = " ".join(
        [
            profile.major or "",
            profile.experience_summary or "",
            *profile.skills,
            *profile.projects,
            *profile.certificates,
        ]
    ).lower()
    scored = [
        (sum(keyword in text for keyword in keywords), role)
        for role, keywords in _ROLE_KEYWORDS.items()
    ]
    roles = [role for score, role in sorted(scored, reverse=True) if score > 0]
    return roles[:3] or ["소프트웨어 개발자"]


def _fallback_queries(
    roles: Sequence[str], request: JobRecommendationRequest
) -> List[str]:
    year = date.today().year
    level = "신입" if request.profile.experience_years < 1 else "경력"
    role = roles[0]
    skills = " ".join(request.profile.skills[:3])
    location = " ".join(request.locations[:2])
    company = request.target_companies[0] if request.target_companies else ""
    queries = [
        f"{year} {level} {role} {skills} 채용 {location}",
        f"현재 모집 중 {role} 채용 공고 {location}",
        f"{role} {skills} 정규직 채용",
        f"{role} 지원자격 우대사항 채용",
    ]
    if company:
        queries.insert(0, f"{company} 공식 채용 {role} 지원")
    return [query.strip() for query in queries]


def _complete_queries(
    generated: Sequence[str],
    roles: Sequence[str],
    request: JobRecommendationRequest,
) -> List[str]:
    combined = [
        query.strip()
        for query in [*generated, *_fallback_queries(roles, request)]
        if query and query.strip()
    ]
    return list(dict.fromkeys(combined))[:6]


def _deduplicate_hits(hits: Iterable[JobSearchHit]) -> List[JobSearchHit]:
    selected: dict[str, JobSearchHit] = {}
    for hit in hits:
        key = canonical_url(hit.url)
        if not key or key in selected:
            continue
        selected[key] = JobSearchHit(hit.title, key, hit.content, hit.query)
    return list(selected.values())


def _deduplicate_verified_pages(
    pages: Iterable[VerifiedJobPage],
) -> List[VerifiedJobPage]:
    selected: dict[str, VerifiedJobPage] = {}
    for page in pages:
        key = canonical_url(page.final_url)
        current = selected.get(key)
        if current is None or (
            current.verification_status != "verified_active"
            and page.verification_status == "verified_active"
        ):
            selected[key] = page
    return list(selected.values())


def _aggregate_requirements(
    jobs: Sequence[JobRecommendation],
    attribute: str,
    category: Literal["required", "preferred"],
) -> List[RequirementInsight]:
    evidence: dict[str, dict[str, object]] = {}
    for job in jobs:
        seen_in_job: set[str] = set()
        for requirement in getattr(job, attribute):
            key = compact(requirement)
            if not key or key in seen_in_job:
                continue
            seen_in_job.add(key)
            current = evidence.setdefault(
                key,
                {"requirement": requirement, "urls": []},
            )
            urls = current["urls"]
            if isinstance(urls, list) and job.url not in urls:
                urls.append(job.url)
    insights = [
        RequirementInsight(
            requirement=str(value["requirement"]),
            category=category,
            source_count=len(value["urls"]),
            source_job_urls=value["urls"],
        )
        for value in evidence.values()
        if isinstance(value["urls"], list) and len(value["urls"]) >= 2
    ]
    insights.sort(key=lambda item: (-item.source_count, item.requirement))
    return insights


def _find_priority_gaps(
    required: Sequence[RequirementInsight],
    preferred: Sequence[RequirementInsight],
    profile: CareerProfileDto,
) -> List[RequirementGap]:
    gaps = []
    for insight in [*required, *preferred]:
        if profile_matches_requirement(insight.requirement, profile):
            continue
        gaps.append(
            RequirementGap(
                requirement=insight.requirement,
                category=insight.category,
                source_count=insight.source_count,
                reason="입력된 이력에서 해당 요건을 입증할 근거를 찾지 못했습니다.",
            )
        )
    return gaps[:10]


def _fallback_roadmap(
    request: CareerRoadmapRequest,
    gaps: Sequence[RequirementGap],
) -> CareerRoadmapDraft:
    focus = gaps[0].requirement if gaps else f"{request.target_role} 핵심 역량"
    return CareerRoadmapDraft.model_validate(
        {
            "current_fit_summary": (
                f"현재 입력된 이력을 기준으로 {request.target_role} 준비도를 점검했습니다. "
                "실제 공고의 필수요건을 지원 전에 다시 확인해야 합니다."
            ),
            "milestones": [
                {
                    "horizon": "1개월",
                    "objective": f"{focus}의 현재 수준과 부족한 근거를 확인합니다.",
                    "actions": [
                        "검증된 공고의 요건과 보유 근거를 표로 정리합니다.",
                        f"{focus} 관련 학습 또는 실습을 시작합니다.",
                    ],
                    "completion_criteria": [
                        "요건·보유근거·부족근거 표를 완성합니다.",
                        "최소 하나의 실습 결과물을 남깁니다.",
                    ],
                },
                {
                    "horizon": "3개월",
                    "objective": f"{request.target_role} 역량을 결과물로 증명합니다.",
                    "actions": [
                        "목표 공고와 연결되는 프로젝트를 완성합니다.",
                        "문제·행동·결과가 드러나는 프로젝트 설명을 작성합니다.",
                    ],
                    "completion_criteria": [
                        "실행 가능한 프로젝트와 README를 공개합니다.",
                        "핵심 선택과 결과를 설명할 사례를 2개 준비합니다.",
                    ],
                },
                {
                    "horizon": "6개월",
                    "objective": "검증된 공고에 맞춘 지원과 피드백 반복 구조를 만듭니다.",
                    "actions": [
                        "매주 유효 공고를 확인하고 우선순위를 갱신합니다.",
                        "지원 결과와 피드백을 다음 지원 자료에 반영합니다.",
                    ],
                    "completion_criteria": [
                        "적합도 기준을 충족한 공고 지원 기록을 유지합니다.",
                        "피드백에 따른 개선 내역을 남깁니다.",
                    ],
                },
                {
                    "horizon": "12개월",
                    "objective": f"{request.target_role} 지원 경쟁력을 반복 가능한 수준으로 높입니다.",
                    "actions": [
                        "축적한 프로젝트와 지원 피드백을 포트폴리오에 통합합니다.",
                        "분기별로 목표 기업과 직무 요건 변화를 다시 점검합니다.",
                    ],
                    "completion_criteria": [
                        "핵심 역량별 최신 증빙 자료를 하나 이상 유지합니다.",
                        "목표 공고 기준의 분기별 자기 점검 기록을 4회 남깁니다.",
                    ],
                },
            ],
        }
    )
