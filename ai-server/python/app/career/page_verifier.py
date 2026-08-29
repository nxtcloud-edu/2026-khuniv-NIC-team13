"""Bounded job-page fetching and active-posting verification."""
from __future__ import annotations

import html
import ipaddress
import logging
import re
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx

from app.career.models import JobSearchHit, VerifiedJobPage

logger = logging.getLogger(__name__)

_TRACKING_QUERY_PREFIXES = ("utm_", "fbclid", "gclid", "ref", "source")
_INACTIVE_MARKERS = (
    "채용 마감",
    "접수 마감",
    "지원 마감",
    "모집 마감",
    "모집 종료",
    "접수 종료",
    "채용 종료",
    "채용이 종료",
    "마감된 공고",
    "공고가 종료",
)
_JOB_MARKERS = (
    "지원하기",
    "입사지원",
    "채용",
    "모집",
    "담당업무",
    "자격요건",
    "지원자격",
    "우대사항",
)
_HTML_NOISE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")


def is_allowed_external_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    hostname = parsed.hostname.lower().rstrip(".")
    if (
        hostname == "localhost"
        or hostname.endswith((".localhost", ".local", ".internal"))
        or hostname in {"metadata.google.internal", "instance-data"}
    ):
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return True
    return address.is_global


def canonical_url(value: str) -> str:
    if not is_allowed_external_url(value):
        return ""
    parsed = urlsplit(value.strip())
    query = urlencode(
        sorted(
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith(_TRACKING_QUERY_PREFIXES)
        )
    )
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            query,
            "",
        )
    )


def _source_domain(value: str) -> str:
    try:
        return (urlsplit(value).hostname or "").lower()
    except ValueError:
        return ""


def _html_to_text(value: str) -> str:
    value = _HTML_NOISE.sub(" ", value)
    value = _HTML_TAG.sub(" ", value)
    return _WHITESPACE.sub(" ", html.unescape(value)).strip()


def _decode_body(body: bytes, content_type: str) -> str:
    charset_match = re.search(r"charset=([^;\s]+)", content_type, re.IGNORECASE)
    encodings = [charset_match.group(1)] if charset_match else []
    encodings.extend(["utf-8", "cp949"])
    for encoding in encodings:
        try:
            return body.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")


class JobPageVerifier:
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None) -> None:
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            timeout=12.0,
            follow_redirects=False,
            headers={"User-Agent": "PertineoCareerBot/1.0 (+job-link-validation)"},
        )

    async def verify(self, hit: JobSearchHit, candidate_id: str) -> VerifiedJobPage:
        final_url = hit.url
        source_domain = _source_domain(hit.url)
        try:
            fetched = await self._fetch_bounded(hit.url)
            if fetched is None:
                return VerifiedJobPage(
                    candidate_id, hit, final_url, source_domain, "", "unknown"
                )
            status_code, headers, final_url, body = fetched
            source_domain = _source_domain(final_url)
            if not 200 <= status_code < 300:
                return VerifiedJobPage(
                    candidate_id, hit, final_url, source_domain, "", "unknown"
                )
            content_type = headers.get("content-type", "").lower()
            if content_type and not any(
                content_kind in content_type
                for content_kind in ("text/", "application/xhtml+xml")
            ):
                return VerifiedJobPage(
                    candidate_id, hit, final_url, source_domain, "", "unknown"
                )
            page_text = _html_to_text(_decode_body(body, content_type))[:20_000]
            normalized = page_text.lower()
            if any(marker in normalized for marker in _INACTIVE_MARKERS):
                status = "inactive"
            elif sum(marker in normalized for marker in _JOB_MARKERS) >= 2:
                status = "verified_active"
            else:
                status = "unknown"
            return VerifiedJobPage(
                candidate_id,
                hit,
                final_url,
                source_domain,
                page_text,
                status,
            )
        except (httpx.HTTPError, ValueError) as exc:
            logger.info(
                "Job URL verification failed: domain=%s error_type=%s",
                source_domain,
                type(exc).__name__,
            )
            return VerifiedJobPage(
                candidate_id, hit, final_url, source_domain, "", "unknown"
            )

    async def _fetch_bounded(
        self, initial_url: str
    ) -> Optional[tuple[int, httpx.Headers, str, bytes]]:
        current_url = initial_url
        for _ in range(4):
            if not is_allowed_external_url(current_url):
                return None
            async with self._client.stream(
                "GET", current_url, headers={"Range": "bytes=0-524287"}
            ) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        return None
                    current_url = urljoin(str(response.url), location)
                    continue
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    remaining = 524_288 - len(body)
                    if remaining <= 0:
                        break
                    body.extend(chunk[:remaining])
                return response.status_code, response.headers, str(response.url), bytes(body)
        return None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
