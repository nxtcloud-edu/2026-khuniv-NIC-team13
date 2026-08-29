from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.controllers.career_controller import router
from app.schemas.career import (
    ApplicantAxisScores,
    CareerMilestone,
    CareerRoadmapResponse,
    CompanyRecommendationResponse,
    JobRecommendationResponse,
    RoleRecommendation,
)


class FakeCareerService:
    async def recommend(self, payload):
        assert payload.target_roles == []
        return JobRecommendationResponse(
            generated_at=datetime.now(timezone.utc),
            resolved_target_roles=["백엔드 개발자"],
            search_queries=["백엔드 개발자 채용"],
            searched_candidate_count=2,
            verified_candidate_count=0,
            jobs=[],
            notice="검증된 공고가 없습니다.",
        )

    async def roadmap(self, payload):
        assert payload.target_role == "백엔드 개발자"
        assert payload.target_company == "테스트기업"
        return CareerRoadmapResponse(
            generated_at=datetime.now(timezone.utc),
            target_role=payload.target_role,
            target_company=payload.target_company,
            current_fit_summary="현재 적합도 요약",
            common_required_requirements=[],
            common_preferred_requirements=[],
            priority_gaps=[],
            milestones=[
                CareerMilestone(
                    horizon=horizon,
                    objective=f"{horizon} 목표",
                    actions=["실행"],
                    completion_criteria=["완료 기준"],
                )
                for horizon in ("1개월", "3개월", "6개월", "12개월")
            ],
            reference_jobs=[],
            notice=None,
        )

    async def recommend_companies(self, payload):
        assert payload.question_list == ["문제 해결 경험"]
        assert payload.answer_list == ["API 성능을 개선했습니다."]
        return CompanyRecommendationResponse(
            generated_at=datetime.now(timezone.utc),
            resolved_track="engineering",
            resolved_target_roles=["백엔드 개발자"],
            role_recommendations=[
                RoleRecommendation(
                    role="백엔드 개발자", evidence=["API 개선 경험"]
                )
            ],
            applicant_scores=ApplicantAxisScores(x=4.0, y=3.9, z=4.1),
            considered_company_count=0,
            verified_company_count=0,
            companies=[],
            methodology_notice="합격 확률이 아닌 과거 합격 사례 대비 적합도입니다.",
            notice="조건을 충족한 기업이 없습니다.",
        )


def test_recommendations_route_accepts_profile_without_target_roles():
    app = FastAPI()
    app.include_router(router)
    app.state.container = SimpleNamespace(career_service=FakeCareerService())
    client = TestClient(app)

    response = client.post(
        "/api/career/recommendations",
        json={
            "profile": {
                "userId": "user-1",
                "experienceYears": 0,
                "skills": ["Python", "FastAPI"],
            },
            "candidateLimit": 10,
            "resultLimit": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["resolvedTargetRoles"] == ["백엔드 개발자"]
    assert body["searchedCandidateCount"] == 2
    assert body["verifiedCandidateCount"] == 0
    assert body["jobs"] == []


def test_roadmap_route_returns_exact_four_horizons():
    app = FastAPI()
    app.include_router(router)
    app.state.container = SimpleNamespace(career_service=FakeCareerService())
    client = TestClient(app)

    response = client.post(
        "/api/career/roadmap",
        json={
            "profile": {
                "userId": "user-1",
                "experienceYears": 1,
                "skills": ["Python"],
            },
            "targetRole": "백엔드 개발자",
            "targetCompany": "테스트기업",
            "candidateLimit": 10,
        },
    )

    assert response.status_code == 200
    assert [item["horizon"] for item in response.json()["milestones"]] == [
        "1개월",
        "3개월",
        "6개월",
        "12개월",
    ]


def test_company_recommendations_route_accepts_self_introduction():
    app = FastAPI()
    app.include_router(router)
    app.state.container = SimpleNamespace(career_service=FakeCareerService())
    client = TestClient(app)

    response = client.post(
        "/api/career/company-recommendations",
        json={
            "profile": {"userId": "user-1", "skills": ["Python", "FastAPI"]},
            "questionList": ["문제 해결 경험"],
            "answerList": ["API 성능을 개선했습니다."],
            "minimumSampleCount": 10,
            "companyCandidateLimit": 6,
            "resultLimit": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["resolvedTrack"] == "engineering"
    assert body["roleRecommendations"][0]["evidence"] == ["API 개선 경험"]
    assert body["companies"] == []
