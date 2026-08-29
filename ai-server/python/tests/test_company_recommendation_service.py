import json

import pytest

from app.career.models import (
    ApplicantAxisAssessment,
    ApplicantCompanyAssessment,
    ExtractedJob,
    JobSearchHit,
    RoleRecommendationEvidence,
    VerifiedJobPage,
)
from app.career.llm_client import CareerLlmClient
from app.career.service import CareerRecommendationService
from app.repository.models import HistoricalCompanyStats
from app.schemas.career import CareerProfileDto, CompanyRecommendationRequest
from app.workflow.track import Track


def _request() -> CompanyRecommendationRequest:
    return CompanyRecommendationRequest(
        profile=CareerProfileDto(
            user_id="user-1",
            major="컴퓨터공학",
            experience_years=1,
            experience_summary="백엔드 개발 인턴 경험",
            skills=["Python", "FastAPI", "AWS"],
            projects=["실시간 이벤트 처리 API 개발"],
        ),
        question_list=["문제를 해결한 경험을 작성해주세요."],
        answer_list=[
            "인턴 중 API 병목을 분석해 응답 시간을 800ms에서 120ms로 개선했습니다."
        ],
        locations=["서울"],
        minimum_sample_count=10,
        company_candidate_limit=4,
        result_limit=3,
    )


class FakeCompanyLlmClient:
    async def assess_company_candidate(self, request):
        assert request.question_list
        return ApplicantCompanyAssessment(
            track=Track.ENGINEERING,
            role_recommendations=[
                RoleRecommendationEvidence(
                    role="백엔드 개발자",
                    evidence=[
                        "FastAPI 기반 백엔드 개발 경험",
                        "API 응답 시간을 수치로 개선한 경험",
                    ],
                )
            ],
            x=ApplicantAxisAssessment(
                score=4.2,
                evidence=["병목 원인을 분석하고 개선 방법을 설계했습니다."],
            ),
            y=ApplicantAxisAssessment(
                score=4.0,
                evidence=["백엔드 인턴으로 실제 API를 개선했습니다."],
            ),
            z=ApplicantAxisAssessment(
                score=4.1,
                evidence=["응답 시간을 800ms에서 120ms로 개선했습니다."],
            ),
        )

    async def extract_jobs(self, pages):
        return [
            ExtractedJob(
                candidate_id=page.candidate_id,
                company=page.hit.title.removesuffix(" 백엔드 채용"),
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


class FakeHistoryRepository:
    def __init__(self) -> None:
        self.calls = []

    async def list_company_track_stats(self, track, minimum_sample_count):
        self.calls.append((track, minimum_sample_count))
        return [
            HistoricalCompanyStats(
                company="알파",
                track="engineering",
                sample_count=30,
                x=3.5,
                y=3.7,
                z=3.8,
                overall=3.67,
            ),
            HistoricalCompanyStats(
                company="베타",
                track="engineering",
                sample_count=20,
                x=3.9,
                y=3.8,
                z=3.9,
                overall=3.87,
            ),
            HistoricalCompanyStats(
                company="감마",
                track="engineering",
                sample_count=40,
                x=4.3,
                y=4.2,
                z=4.2,
                overall=4.23,
            ),
            HistoricalCompanyStats(
                company="델타",
                track="engineering",
                sample_count=10,
                x=4.4,
                y=4.4,
                z=4.4,
                overall=4.4,
            ),
        ]


class FakeCompanySearchClient:
    def __init__(self) -> None:
        self.queries = []

    async def search(self, query, max_results=5):
        del max_results
        self.queries.append(query)
        company = query.split(" 공식 채용", 1)[0]
        return [
            JobSearchHit(
                title=f"{company} 백엔드 채용",
                url=f"https://jobs.example.com/{company}",
                content="백엔드 개발자 Python FastAPI AWS 서울 채용",
                query=query,
            )
        ]

    async def aclose(self):
        return None


class FakeCompanyVerifier:
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
async def test_company_recommendation_uses_history_before_live_job_ranking():
    history = FakeHistoryRepository()
    search = FakeCompanySearchClient()
    service = CareerRecommendationService(
        llm_client=FakeCompanyLlmClient(),
        search_client=search,
        page_verifier=FakeCompanyVerifier(),
        previous_resume_data_repository=history,
    )

    result = await service.recommend_companies(_request())

    assert history.calls == [("engineering", 10)]
    assert result.resolved_track == "engineering"
    assert result.resolved_target_roles == ["백엔드 개발자"]
    assert result.role_recommendations[0].evidence
    assert result.considered_company_count == 4
    assert result.verified_company_count == 4
    assert [item.company for item in result.companies] == ["알파", "베타", "감마"]
    assert all(item.active_job.verification_status == "verified_active" for item in result.companies)
    assert all(item.historical_sample_count >= 10 for item in result.companies)
    assert all(item.recommendation_evidence for item in result.companies)
    assert all(item.fit_score == sum(item.score_breakdown.model_dump().values()) for item in result.companies)
    assert any(query.startswith("알파 공식 채용") for query in search.queries)


@pytest.mark.asyncio
async def test_company_recommendation_returns_notice_when_no_history_is_eligible():
    history = FakeHistoryRepository()

    async def no_history(track, minimum_sample_count):
        del track, minimum_sample_count
        return []

    history.list_company_track_stats = no_history
    search = FakeCompanySearchClient()
    service = CareerRecommendationService(
        llm_client=FakeCompanyLlmClient(),
        search_client=search,
        page_verifier=FakeCompanyVerifier(),
        previous_resume_data_repository=history,
    )

    result = await service.recommend_companies(_request())

    assert result.companies == []
    assert result.considered_company_count == 0
    assert "표본" in result.notice
    assert search.queries == []


@pytest.mark.asyncio
async def test_company_assessment_excludes_identity_and_raw_resume(monkeypatch):
    captured = {}

    async def fake_parse_structured(client, system, user, response_model, **kwargs):
        del client, response_model, kwargs
        captured["system"] = system
        captured["payload"] = json.loads(user)
        return await FakeCompanyLlmClient().assess_company_candidate(_request())

    monkeypatch.setattr("app.career.llm_client.parse_structured", fake_parse_structured)
    request = _request()
    request.profile.resume_text = "name@example.com 010-1234-5678"

    await CareerLlmClient(client=object()).assess_company_candidate(request)

    assert "user_id" not in captured["payload"]["profile"]
    assert "resume_text" not in captured["payload"]["profile"]
    assert captured["payload"]["self_introduction"][0]["answer"].startswith("인턴 중")
    assert "engineering_track_rubric" in captured["system"]
    assert "business_track_rubric" in captured["system"]
