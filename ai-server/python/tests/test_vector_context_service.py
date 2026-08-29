from typing import Dict, List, Optional

import pytest

from app.repository.previous_resume_data_repository import PreviousResumeDataRepository
from app.vector.vector_context_service import VectorContextRequest, VectorContextService


class FakeVectorEmbedder:
    def __init__(self, embedding: List[float]):
        self._embedding = embedding

    async def create_embedding(self, company, job_position, question_list, answer_list):
        return self._embedding


class FakeVectorSearchService:
    def __init__(self, keys: List[str], failing: bool = False):
        self._keys = keys
        self._failing = failing
        self.last_top_k: Optional[int] = None

    @staticmethod
    def failing() -> "FakeVectorSearchService":
        return FakeVectorSearchService([], True)

    async def search_top_k_documents(self, embedding, top_k):
        self.last_top_k = top_k
        if self._failing:
            raise RuntimeError("vector failure")
        return self._keys


class FakePreviousResumeDataRepository(PreviousResumeDataRepository):
    def __init__(self, documents: Dict[str, str], failing_keys: Optional[List[str]] = None):
        self._documents = documents
        self._failing_keys = failing_keys or []
        self.lookup_count = 0

    async def get_score_by_company_and_track(self, company, track):
        return None

    async def get_score_by_track(self, track):
        return None

    async def list_company_track_stats(self, track, minimum_sample_count):
        return []

    async def get_resume_text(self, id_):
        self.lookup_count += 1
        if id_ in self._failing_keys:
            raise RuntimeError("repo failure")
        return self._documents.get(id_)


def request() -> VectorContextRequest:
    return VectorContextRequest("삼성", "백엔드", ["질문"], ["답변"])


@pytest.mark.asyncio
async def test_builds_context_from_top_k_resolved_documents():
    search_service = FakeVectorSearchService(["resume-1", "resume-2", "resume-3"])
    service = VectorContextService(
        FakeVectorEmbedder([0.1, 0.2]),
        search_service,
        FakePreviousResumeDataRepository(
            {
                "resume-1": "첫 번째 합격자 문서",
                "resume-2": "두 번째 합격자 문서",
                "resume-3": "세 번째 합격자 문서",
            }
        ),
    )

    result = await service.build_evaluation_context(request())

    assert result.status == "success"
    assert result.selected_keys == ["resume-1", "resume-2", "resume-3"]
    assert result.documents == ["첫 번째 합격자 문서", "두 번째 합격자 문서", "세 번째 합격자 문서"]
    assert "첫 번째 합격자 문서" in result.to_prompt_text()
    assert search_service.last_top_k == 3


@pytest.mark.asyncio
async def test_returns_empty_context_when_search_returns_no_keys():
    repository = FakePreviousResumeDataRepository({})
    service = VectorContextService(
        FakeVectorEmbedder([0.1, 0.2]),
        FakeVectorSearchService([]),
        repository,
    )

    result = await service.build_evaluation_context(request())

    assert result.status == "empty"
    assert result.selected_keys == []
    assert result.documents == []
    assert result.to_prompt_text() == "유사 합격자 자기소개서 데이터 없음"
    assert repository.lookup_count == 0


@pytest.mark.asyncio
async def test_returns_empty_context_when_vector_search_fails():
    service = VectorContextService(
        FakeVectorEmbedder([0.1, 0.2]),
        FakeVectorSearchService.failing(),
        FakePreviousResumeDataRepository({}),
    )

    result = await service.build_evaluation_context(request())

    assert result.status == "failure"
    assert result.selected_keys == []
    assert result.documents == []


@pytest.mark.asyncio
async def test_skips_missing_documents():
    service = VectorContextService(
        FakeVectorEmbedder([0.1, 0.2]),
        FakeVectorSearchService(["resume-1", "resume-2"]),
        FakePreviousResumeDataRepository({"resume-1": "첫 번째 합격자 문서"}),
    )

    result = await service.build_evaluation_context(request())

    assert result.status == "success"
    assert result.selected_keys == ["resume-1", "resume-2"]
    assert result.documents == ["첫 번째 합격자 문서"]


@pytest.mark.asyncio
async def test_continues_when_repository_lookup_fails():
    service = VectorContextService(
        FakeVectorEmbedder([0.1, 0.2]),
        FakeVectorSearchService(["resume-1", "resume-2"]),
        FakePreviousResumeDataRepository({"resume-2": "두 번째 합격자 문서"}, failing_keys=["resume-1"]),
    )

    result = await service.build_evaluation_context(request())

    assert result.status == "success"
    assert result.documents == ["두 번째 합격자 문서"]
