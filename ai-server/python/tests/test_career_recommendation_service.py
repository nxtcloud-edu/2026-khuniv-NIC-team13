import json
from datetime import datetime, timezone

import httpx
import pytest

from app.career.models import (
    ExtractedJob,
    JobDiscoveryPlan,
    JobSearchHit,
    VerifiedJobPage,
)
from app.career.llm_client import CareerLlmClient
from app.career.page_verifier import (
    JobPageVerifier,
    canonical_url,
    is_allowed_external_url,
)
from app.career.service import CareerRecommendationService
from app.schemas.career import CareerProfileDto, JobRecommendationRequest


def _request(**overrides) -> JobRecommendationRequest:
    payload = {
        "profile": CareerProfileDto(
            user_id="user-1",
            major="컴퓨터공학",
            experience_years=1,
            experience_summary="FastAPI 백엔드 인턴 경험",
            skills=["Python", "FastAPI", "AWS"],
            projects=["FastAPI 서비스 개발 및 배포"],
        ),
        "target_roles": [],
        "locations": ["서울"],
        "candidate_limit": 10,
        "result_limit": 3,
    }
    payload.update(overrides)
    return JobRecommendationRequest(**payload)


class FakeLlmClient:
    def __init__(self, fail_plan: bool = False) -> None:
        self.fail_plan = fail_plan

    async def plan_discovery(self, request):
        if self.fail_plan:
            raise RuntimeError("planner unavailable")
        return JobDiscoveryPlan(
            target_roles=["백엔드 개발자", "플랫폼 엔지니어"],
            queries=[
                "백엔드 개발자 채용",
                "Python FastAPI 채용",
                "플랫폼 엔지니어 채용",
                "AWS 백엔드 신입 채용",
            ],
        )

    async def extract_jobs(self, pages):
        return [
            ExtractedJob(
                candidate_id=page.candidate_id,
                company=f"기업-{page.candidate_id}",
                title="백엔드 개발자",
                deadline="2099-12-31",
                location="서울",
                employment_type="정규직",
                experience_level="신입",
                required_requirements=["Python", "FastAPI"],
                preferred_requirements=["AWS"],
            )
            for page in pages
        ]

    async def aclose(self):
        return None


class FakeSearchClient:
    async def search(self, query, max_results=5):
        del max_results
        suffix = abs(hash(query)) % 5
        return [
            JobSearchHit(
                title=f"채용 {suffix}",
                url=f"https://jobs.example.com/posting/{suffix}?utm_source=test",
                content="백엔드 개발자 Python FastAPI 서울 채용",
                query=query,
            ),
            JobSearchHit(
                title=f"채용 {suffix}",
                url=f"https://jobs.example.com/posting/{suffix}",
                content="중복 공고",
                query=query,
            ),
        ]

    async def aclose(self):
        return None


class FakeVerifier:
    async def verify(self, hit, candidate_id):
        return VerifiedJobPage(
            candidate_id=candidate_id,
            hit=hit,
            final_url=hit.url,
            source_domain="jobs.example.com",
            page_text="지원하기 채용 담당업무 자격요건 Python FastAPI AWS",
            verification_status="verified_active",
        )

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_recommendation_infers_roles_deduplicates_and_returns_top_three():
    service = CareerRecommendationService(
        llm_client=FakeLlmClient(),
        search_client=FakeSearchClient(),
        page_verifier=FakeVerifier(),
    )

    result = await service.recommend(_request())

    assert result.resolved_target_roles == ["백엔드 개발자", "플랫폼 엔지니어"]
    assert len(result.search_queries) >= 4
    assert result.searched_candidate_count <= 10
    assert result.verified_candidate_count >= 3
    assert len(result.jobs) == 3
    assert all(job.verification_status == "verified_active" for job in result.jobs)
    assert all(job.fit_score >= 80 for job in result.jobs)
    assert all(job.matched_requirements for job in result.jobs)
    assert len({job.url for job in result.jobs}) == 3


@pytest.mark.asyncio
async def test_recommendation_uses_deterministic_role_fallback_when_planner_fails():
    service = CareerRecommendationService(
        llm_client=FakeLlmClient(fail_plan=True),
        search_client=FakeSearchClient(),
        page_verifier=FakeVerifier(),
    )

    result = await service.recommend(_request())

    assert "백엔드 개발자" in result.resolved_target_roles
    assert len(result.search_queries) >= 4


@pytest.mark.asyncio
async def test_recommendation_preserves_explicit_target_roles():
    service = CareerRecommendationService(
        llm_client=FakeLlmClient(),
        search_client=FakeSearchClient(),
        page_verifier=FakeVerifier(),
    )

    result = await service.recommend(_request(target_roles=["서버 개발자"]))

    assert result.resolved_target_roles == ["서버 개발자"]


@pytest.mark.asyncio
async def test_discovery_plan_excludes_user_id_and_raw_resume(monkeypatch):
    captured = {}

    async def fake_parse_structured(client, system, user, response_model, **kwargs):
        del client, system, response_model, kwargs
        captured.update(json.loads(user))
        return JobDiscoveryPlan(
            target_roles=["백엔드 개발자"],
            queries=["q1", "q2", "q3", "q4"],
        )

    monkeypatch.setattr("app.career.llm_client.parse_structured", fake_parse_structured)
    request = _request()
    request.profile.resume_text = "name@example.com 010-1234-5678"

    await CareerLlmClient(client=object()).plan_discovery(request)

    assert "user_id" not in captured["profile"]
    assert "resume_text" not in captured["profile"]


def test_external_url_policy_rejects_local_and_private_hosts():
    assert is_allowed_external_url("https://jobs.example.com/posting/1")
    assert not is_allowed_external_url("http://localhost:8080/private")
    assert not is_allowed_external_url("http://127.0.0.1/private")
    assert not is_allowed_external_url("http://169.254.169.254/latest/meta-data")


def test_canonical_url_removes_tracking_and_fragment():
    assert canonical_url(
        "https://Jobs.Example.com/posting/1/?utm_source=test&team=ai#apply"
    ) == "https://jobs.example.com/posting/1?team=ai"
    assert canonical_url("not-a-url") == ""


@pytest.mark.asyncio
async def test_page_verifier_distinguishes_active_and_inactive_pages():
    def handler(request: httpx.Request) -> httpx.Response:
        body = (
            "채용 마감 모집 종료"
            if "closed" in str(request.url)
            else "지원하기 채용 담당업무 자격요건"
        )
        return httpx.Response(200, text=body, headers={"content-type": "text/html"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        verifier = JobPageVerifier(http_client=client)
        active_hit = JobSearchHit("active", "https://jobs.example.com/active", "", "q")
        closed_hit = JobSearchHit("closed", "https://jobs.example.com/closed", "", "q")

        active = await verifier.verify(active_hit, "job-1")
        closed = await verifier.verify(closed_hit, "job-2")

    assert active.verification_status == "verified_active"
    assert closed.verification_status == "inactive"


def test_recommendation_serializes_auditable_score_breakdown():
    from app.schemas.career import FitScoreBreakdown, JobRecommendation

    job = JobRecommendation(
        company="테스트",
        title="백엔드 개발자",
        url="https://jobs.example.com/1",
        source_domain="jobs.example.com",
        verification_status="verified_active",
        fit_score=95,
        score_breakdown=FitScoreBreakdown(
            role=30,
            required=35,
            preferred=10,
            experience=10,
            location=5,
            verification=5,
        ),
        recommendation_reason="근거",
        checked_at=datetime.now(timezone.utc),
    )

    assert sum(job.score_breakdown.model_dump().values()) == job.fit_score
