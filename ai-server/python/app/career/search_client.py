"""Tavily adapter dedicated to current job posting discovery."""
from __future__ import annotations

from typing import List, Optional

import httpx

from app.career.errors import CareerConfigurationError
from app.career.models import JobSearchHit
from app.career.page_verifier import is_allowed_external_url
from app.config.settings import Settings, get_settings

_TAVILY_URL = "https://api.tavily.com/search"


class TavilyJobSearchClient:
    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=30.0)

    async def search(self, query: str, max_results: int = 5) -> List[JobSearchHit]:
        if not self._settings.tavily_api_key:
            raise CareerConfigurationError(
                "TAVILY_API_KEY가 설정되지 않아 채용공고를 검색할 수 없습니다."
            )
        response = await self._client.post(
            _TAVILY_URL,
            headers={"Content-Type": "application/json"},
            json={
                "api_key": self._settings.tavily_api_key,
                "query": query,
                "include_answer": False,
                "max_results": max(1, min(max_results, 5)),
                "search_depth": "advanced",
            },
        )
        response.raise_for_status()
        hits: List[JobSearchHit] = []
        for item in response.json().get("results") or []:
            url = str(item.get("url") or "").strip()
            if not is_allowed_external_url(url):
                continue
            hits.append(
                JobSearchHit(
                    title=str(item.get("title") or "채용공고").strip(),
                    url=url,
                    content=str(item.get("content") or "").strip(),
                    query=query,
                )
            )
        return hits

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
