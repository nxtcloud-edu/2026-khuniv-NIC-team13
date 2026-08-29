import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.career.models import CareerRoadmapDraft
from app.career.llm_client import CareerLlmClient
from app.career.service import CareerRecommendationService
from app.schemas.career import (
    CareerProfileDto,
    CareerRoadmapRequest,
    FitScoreBreakdown,
    JobRecommendation,
    JobRecommendationResponse,
)


def _job(
    index: int,
    *,
    required: list[str],
    preferred: list[str],
) -> JobRecommendation:
    return JobRecommendation(
        company=f"기업-{index}",
        title="백엔드 개발자",
        url=f"https://jobs.example.com/{index}",
        source_domain="jobs.example.com",
        verification_status="verified_active",
        fit_score=80,
        score_breakdown=FitScoreBreakdown(
            role=30,
            required=20,
            preferred=5,
            experience=10,
            location=10,
            verification=5,
        ),
        required_requirements=required,
        preferred_requirements=preferred,
        matched_requirements=["Python"],
        missing_requirements=[item for item in required if item != "Python"],
        recommendation_reason="근거",
        checked_at=datetime.now(timezone.utc),
    )


def _request() -> CareerRoadmapRequest:
    return CareerRoadmapRequest(
        profile=CareerProfileDto(
            user_id="user-1",
            experience_years=1,
            skills=["Python"],
            resume_text="name@example.com 010-1234-5678",
        ),
        target_role="백엔드 개발자",
        target_company="테스트기업",
        locations=["서울"],
        candidate_limit=10,
    )


def _draft() -> CareerRoadmapDraft:
    return CareerRoadmapDraft.model_validate(
        {
            "current_fit_summary": "Python 근거는 확인되며 배포 역량 보완이 필요합니다.",
            "milestones": [
                {
                    "horizon": horizon,
                    "objective": f"{horizon} 목표",
                    "actions": [f"{horizon} 실행"],
                    "completion_criteria": [f"{horizon} 완료 기준"],
                }
                for horizon in ("1개월", "3개월", "6개월", "12개월")
            ],
        }
    )


class FakeRoadmapLlm:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.received_profile = None

    async def build_roadmap(self, request, required, preferred, gaps, jobs):
        del required, preferred, gaps, jobs
        self.received_profile = request.profile.model_dump(
            exclude={"user_id", "resume_text"}
        )
        if self.fail:
            raise RuntimeError("provider unavailable")
        return _draft()

    async def aclose(self):
        return None


class UnusedClient:
    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_roadmap_aggregates_evidence_gaps_and_exact_horizons(monkeypatch):
    jobs = [
        _job(1, required=["Python", "Docker"], preferred=["AWS"]),
        _job(2, required=["Python", "Kubernetes"], preferred=["AWS"]),
        _job(3, required=["Python", "Docker"], preferred=["CI/CD"]),
    ]
    recommendation = JobRecommendationResponse(
        generated_at=datetime.now(timezone.utc),
        resolved_target_roles=["백엔드 개발자"],
        search_queries=["백엔드 채용"],
        searched_candidate_count=3,
        verified_candidate_count=3,
        jobs=jobs,
    )
    llm = FakeRoadmapLlm()
    service = CareerRecommendationService(
        llm_client=llm,
        search_client=UnusedClient(),
        page_verifier=UnusedClient(),
    )

    async def fake_recommend(request):
        assert request.target_roles == ["백엔드 개발자"]
        assert request.target_companies == ["테스트기업"]
        return recommendation

    monkeypatch.setattr(service, "recommend", fake_recommend)

    result = await service.roadmap(_request())

    required = {item.requirement: item for item in result.common_required_requirements}
    preferred = {item.requirement: item for item in result.common_preferred_requirements}
    assert required["Python"].source_count == 3
    assert required["Docker"].source_count == 2
    assert preferred["AWS"].source_count == 2
    assert [gap.requirement for gap in result.priority_gaps] == ["Docker", "AWS"]
    assert [item.horizon for item in result.milestones] == [
        "1개월",
        "3개월",
        "6개월",
        "12개월",
    ]
    assert llm.received_profile is not None
    assert "user_id" not in llm.received_profile
    assert "resume_text" not in llm.received_profile


@pytest.mark.asyncio
async def test_roadmap_uses_four_horizon_fallback_when_llm_fails(monkeypatch):
    llm = FakeRoadmapLlm(fail=True)
    service = CareerRecommendationService(
        llm_client=llm,
        search_client=UnusedClient(),
        page_verifier=UnusedClient(),
    )
    recommendation = JobRecommendationResponse(
        generated_at=datetime.now(timezone.utc),
        resolved_target_roles=["백엔드 개발자"],
        search_queries=[],
        searched_candidate_count=0,
        verified_candidate_count=0,
        jobs=[],
    )

    async def fake_recommend(request):
        del request
        return recommendation

    monkeypatch.setattr(service, "recommend", fake_recommend)

    result = await service.roadmap(_request())

    assert [item.horizon for item in result.milestones] == [
        "1개월",
        "3개월",
        "6개월",
        "12개월",
    ]
    assert result.reference_jobs == []
    assert "검증된 참고 공고가 없어" in result.notice


def test_roadmap_draft_rejects_missing_or_duplicate_horizons():
    payload = _draft().model_dump()
    payload["milestones"] = payload["milestones"][:3]
    with pytest.raises(ValidationError):
        CareerRoadmapDraft.model_validate(payload)

    payload = _draft().model_dump()
    payload["milestones"][3]["horizon"] = "6개월"
    with pytest.raises(ValidationError):
        CareerRoadmapDraft.model_validate(payload)


@pytest.mark.asyncio
async def test_roadmap_llm_payload_excludes_user_id_and_raw_resume(monkeypatch):
    captured = {}

    async def fake_parse_structured(client, system, user, response_model, **kwargs):
        del client, system, response_model, kwargs
        captured.update(json.loads(user))
        return _draft()

    monkeypatch.setattr("app.career.llm_client.parse_structured", fake_parse_structured)

    await CareerLlmClient(client=object()).build_roadmap(
        _request(), [], [], [], []
    )

    assert "user_id" not in captured["profile"]
    assert "resume_text" not in captured["profile"]
