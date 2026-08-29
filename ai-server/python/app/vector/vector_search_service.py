"""Port of ``pertineo.agent.vector.VectorSearchService`` (S3 Vectors query)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, List

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class VectorSearchService:
    def __init__(self, s3vectors_client: Any) -> None:
        self._client = s3vectors_client
        settings = get_settings()
        self._vector_bucket_name = settings.s3_vectors_bucket
        self._vector_index_name = settings.s3_vectors_index

    async def search_top_k_documents(self, embedding: List[float], top_k: int) -> List[str]:
        return await asyncio.to_thread(self._search_top_k_documents_sync, embedding, top_k)

    def _search_top_k_documents_sync(self, embedding: List[float], top_k: int) -> List[str]:
        try:
            float_embedding = [float(v) for v in embedding]
            response = self._client.query_vectors(
                vectorBucketName=self._vector_bucket_name,
                indexName=self._vector_index_name,
                queryVector={"float32": float_embedding},
                returnMetadata=True,
                returnDistance=True,
                topK=top_k,
            )

            vectors = response.get("vectors") or []
            if not vectors:
                return []

            return [vector["key"] for vector in vectors]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Vector database query failed: topK=%s, failureCategory=%s", top_k, type(exc).__name__)
            raise RuntimeError("벡터 데이터베이스 쿼리 실패") from exc
