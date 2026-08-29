"""Create the query vector used for similar-resume retrieval."""
from __future__ import annotations

from typing import Any, List, Optional

import httpx

from app.config.settings import get_settings
_OPENAI_EMBEDDING_URL = "https://api.openai.com/v1/embeddings"
_EMBEDDING_MODEL = "text-embedding-3-small"


class VectorEmbedder:
    def __init__(
        self,
        http_client: Optional[httpx.AsyncClient] = None,
        settings: Optional[Any] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = http_client or httpx.AsyncClient(timeout=30.0)

    async def create_embedding(
        self,
        company: Optional[str],
        job_position: Optional[str],
        question_list: List[str],
        answer_list: List[str],
    ) -> List[float]:
        input_text = self._create_input_text(company, job_position, question_list, answer_list)

        response = await self._client.post(
            _OPENAI_EMBEDDING_URL,
            headers={
                "Authorization": f"Bearer {self._settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={"input": input_text, "model": _EMBEDDING_MODEL},
        )
        response.raise_for_status()
        payload = response.json()

        data = payload.get("data")
        if not data or not data[0].get("embedding"):
            raise RuntimeError("OpenAI 임베딩 API로부터 유효한 응답을 받지 못했습니다.")

        return data[0]["embedding"]

    def _create_input_text(
        self,
        company: Optional[str],
        job_position: Optional[str],
        question_list: List[str],
        answer_list: List[str],
    ) -> str:
        lines = [f"기업: {company}", f"직무: {job_position}", ""]
        for i, question in enumerate(question_list):
            lines.append(f"질문 {i + 1}: {question}")
            if i < len(answer_list):
                lines.append(f"답변 {i + 1}: {answer_list[i]}")
                lines.append("")
        return "\n".join(lines).strip()
