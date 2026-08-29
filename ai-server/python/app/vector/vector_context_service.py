"""Port of ``pertineo.agent.vector.VectorContextService``."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from app.repository.previous_resume_data_repository import PreviousResumeDataRepository
from app.vector.vector_embedder import VectorEmbedder
from app.vector.vector_search_service import VectorSearchService

logger = logging.getLogger(__name__)

_EVALUATION_TOP_K = 3


@dataclass(frozen=True)
class VectorContextRequest:
    company: Optional[str]
    job_position: Optional[str]
    questions: Optional[List[str]]
    answers: Optional[List[str]]


@dataclass(frozen=True)
class VectorEvaluationContext:
    selected_keys: List[str] = field(default_factory=list)
    documents: List[str] = field(default_factory=list)
    status: str = "empty"

    @staticmethod
    def empty(status: str) -> "VectorEvaluationContext":
        return VectorEvaluationContext([], [], status)

    def to_prompt_text(self) -> str:
        if not self.documents:
            return "유사 합격자 자기소개서 데이터 없음"

        parts = ["벡터 검색으로 찾은 유사 합격자 자기소개서/분석 텍스트:\n"]
        for i, document in enumerate(self.documents):
            parts.append(f"\n[유사 문서 {i + 1}]\n{document}")
        return "".join(parts)


class VectorContextService:
    def __init__(
        self,
        vector_embedder: VectorEmbedder,
        vector_search_service: VectorSearchService,
        previous_resume_data_repository: PreviousResumeDataRepository,
    ) -> None:
        self._vector_embedder = vector_embedder
        self._vector_search_service = vector_search_service
        self._previous_resume_data_repository = previous_resume_data_repository

    async def build_evaluation_context(self, request: VectorContextRequest) -> VectorEvaluationContext:
        try:
            logger.info(
                "vector evaluation context search started: topK=%s, company=%s, jobPosition=%s",
                _EVALUATION_TOP_K,
                request.company,
                request.job_position,
            )

            embedding = await self._vector_embedder.create_embedding(
                request.company,
                request.job_position,
                request.questions or [],
                request.answers or [],
            )
            keys = await self._vector_search_service.search_top_k_documents(embedding, _EVALUATION_TOP_K)

            if not keys:
                logger.warning(
                    "vector evaluation context search returned empty results: topK=%s", _EVALUATION_TOP_K
                )
                return VectorEvaluationContext.empty("empty")

            documents = await self._resolve_documents(keys)
            if not documents:
                logger.warning(
                    "vector evaluation context document resolution returned empty results: "
                    "topK=%s, selectedKeyCount=%s, selectedKeys=%s",
                    _EVALUATION_TOP_K,
                    len(keys),
                    keys,
                )
                return VectorEvaluationContext(keys, [], "missing_documents")

            logger.info(
                "vector evaluation context search succeeded: topK=%s, selectedKeyCount=%s, "
                "resolvedDocumentCount=%s, selectedKeys=%s",
                _EVALUATION_TOP_K,
                len(keys),
                len(documents),
                keys,
            )
            return VectorEvaluationContext(keys, documents, "success")
        except Exception as exc:  # noqa: BLE001 - non-blocking best-effort search
            logger.warning(
                "vector evaluation context search failed non-blockingly: topK=%s, failureCategory=%s",
                _EVALUATION_TOP_K,
                type(exc).__name__,
            )
            return VectorEvaluationContext.empty("failure")

    async def _resolve_documents(self, keys: List[str]) -> List[str]:
        documents: List[str] = []
        for key in keys:
            try:
                document = await self._previous_resume_data_repository.get_resume_text(key)
                if document is not None:
                    documents.append(document)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "vector evaluation context document resolution failed non-blockingly: "
                    "selectedKey=%s, failureCategory=%s",
                    key,
                    type(exc).__name__,
                )
        return documents
