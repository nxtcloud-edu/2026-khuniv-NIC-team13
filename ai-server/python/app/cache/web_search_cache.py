"""Port of ``pertineo.agent.cache.WebSearchCache`` /
``LocalWebSearchCache``.

Uses an in-process TTL cache (30 minute expiry, 1000 entry cap) keyed by
``"{jobPosition}-{company}"``, matching the Caffeine-backed Spring
``@Cacheable``/``@CachePut`` pair in the Java version.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from cachetools import TTLCache

from app.cache.models import CachedTavilyData
from app.config.settings import get_settings


class WebSearchCache(ABC):
    @abstractmethod
    def cache_store(self, position: str, company: str, data: CachedTavilyData) -> CachedTavilyData: ...

    @abstractmethod
    def cache_retrieve(self, position: str, company: str) -> Optional[CachedTavilyData]: ...


class LocalWebSearchCache(WebSearchCache):
    def __init__(self) -> None:
        settings = get_settings()
        self._cache: TTLCache = TTLCache(
            maxsize=settings.web_search_cache_max_size,
            ttl=settings.web_search_cache_ttl_seconds,
        )

    @staticmethod
    def _key(position: str, company: str) -> str:
        return f"{position}-{company}"

    def cache_store(self, position: str, company: str, data: CachedTavilyData) -> CachedTavilyData:
        self._cache[self._key(position, company)] = data
        return data

    def cache_retrieve(self, position: str, company: str) -> Optional[CachedTavilyData]:
        return self._cache.get(self._key(position, company))
