"""Minimal async client for Upstage Solar Embedding 2."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

import httpx

DEFAULT_UPSTAGE_BASE_URL = "https://api.upstage.ai/v1"
DEFAULT_QUERY_MODEL = "solar-embedding-2-query"
DEFAULT_PASSAGE_MODEL = "solar-embedding-2-passage"
MAX_BATCH_TEXTS = 100


@dataclass(frozen=True)
class EmbeddingBatch:
    embeddings: List[List[float]]
    model: str
    prompt_tokens: int


class UpstageEmbeddingClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_UPSTAGE_BASE_URL,
        query_model: str = DEFAULT_QUERY_MODEL,
        passage_model: str = DEFAULT_PASSAGE_MODEL,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._api_key = api_key
        self._url = f"{base_url.rstrip('/')}/embeddings"
        self._query_model = query_model
        self._passage_model = passage_model
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=60.0)

    async def embed_query(self, text: str) -> EmbeddingBatch:
        return await self._embed(text, expected_count=1, model=self._query_model)

    async def embed_passages(self, texts: Sequence[str]) -> EmbeddingBatch:
        normalized = list(texts)
        if not normalized:
            raise ValueError("임베딩할 passage가 없습니다.")
        if len(normalized) > MAX_BATCH_TEXTS:
            raise ValueError(f"Upstage 임베딩 배치는 최대 {MAX_BATCH_TEXTS}개 텍스트를 지원합니다.")
        if any(not text.strip() for text in normalized):
            raise ValueError("비어 있는 passage는 임베딩할 수 없습니다.")
        return await self._embed(normalized, expected_count=len(normalized), model=self._passage_model)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _embed(self, input_: str | List[str], *, expected_count: int, model: str) -> EmbeddingBatch:
        if not self._api_key:
            raise RuntimeError("UPSTAGE_API_KEY가 설정되지 않았습니다.")
        if isinstance(input_, str) and not input_.strip():
            raise ValueError("비어 있는 query는 임베딩할 수 없습니다.")

        response = await self._client.post(
            self._url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={"input": input_, "model": model},
        )
        response.raise_for_status()
        payload = response.json()

        raw_data = payload.get("data")
        if not isinstance(raw_data, list) or len(raw_data) != expected_count:
            raise RuntimeError("Upstage 임베딩 API로부터 유효한 임베딩 응답을 받지 못했습니다.")

        ordered: List[Optional[List[float]]] = [None] * expected_count
        dimension: Optional[int] = None
        for item in raw_data:
            index = item.get("index") if isinstance(item, dict) else None
            embedding = item.get("embedding") if isinstance(item, dict) else None
            if (
                not isinstance(index, int)
                or not 0 <= index < expected_count
                or ordered[index] is not None
                or not isinstance(embedding, list)
                or not embedding
                or not all(isinstance(value, (int, float)) for value in embedding)
            ):
                raise RuntimeError("Upstage 임베딩 API로부터 유효한 임베딩 응답을 받지 못했습니다.")
            if dimension is None:
                dimension = len(embedding)
            elif len(embedding) != dimension:
                raise RuntimeError("Upstage 임베딩 API 응답의 벡터 차원이 일치하지 않습니다.")
            ordered[index] = [float(value) for value in embedding]

        if any(embedding is None for embedding in ordered):
            raise RuntimeError("Upstage 임베딩 API로부터 유효한 임베딩 응답을 받지 못했습니다.")

        usage = payload.get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens", usage.get("total_tokens", 0))
        return EmbeddingBatch(
            embeddings=[embedding for embedding in ordered if embedding is not None],
            model=str(payload.get("model") or model),
            prompt_tokens=int(prompt_tokens or 0),
        )
