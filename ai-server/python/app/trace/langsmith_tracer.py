"""Port of ``pertineo.agent.trace.LangSmithTracer``.

Sends async, best-effort trace spans to the LangSmith runs API. Uses a
``contextvars.ContextVar`` in place of Java's ``ThreadLocal`` to track each
in-flight workflow's dotted-order span chain, since a single workflow run
here executes within one ``asyncio`` task.
"""
from __future__ import annotations

import contextvars
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from app.config.settings import get_settings
from app.util.json_utils import jsonable

logger = logging.getLogger(__name__)

_API_URL = "https://api.smith.langchain.com/runs"
_UNSET_API_KEY = "설정안됨"

_dotted_order_context: contextvars.ContextVar[Dict[str, str]] = contextvars.ContextVar(
    "langsmith_dotted_order_context"
)


def _format_time(dt: datetime) -> str:
    # yyyyMMdd'T'HHmmssSSSSSS'Z' — 6-digit microsecond precision, UTC.
    return dt.strftime("%Y%m%dT%H%M%S%f") + "Z"


class LangSmithTracer:
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None) -> None:
        settings = get_settings()
        self._api_key = settings.langsmith_api_key
        self._project_name = settings.langsmith_project
        self._client = http_client or httpx.AsyncClient(timeout=10.0)

    def _local_map(self) -> Dict[str, str]:
        try:
            return _dotted_order_context.get()
        except LookupError:
            local_map: Dict[str, str] = {}
            _dotted_order_context.set(local_map)
            return local_map

    async def start_trace(self, run_name: str, run_type: str, inputs: Any) -> str:
        return await self.start_span(run_name, run_type, inputs, None, None)

    async def start_span(
        self,
        run_name: str,
        run_type: str,
        inputs: Any,
        trace_id: Optional[str],
        parent_run_id: Optional[str],
    ) -> str:
        run_id = str(uuid.uuid4())
        effective_trace_id = trace_id if trace_id is not None else run_id

        now = datetime.now(timezone.utc)
        current_dotted = f"{_format_time(now)}{run_id}"
        dotted_order = current_dotted

        local_map = self._local_map()
        if parent_run_id is not None and parent_run_id in local_map:
            dotted_order = f"{local_map[parent_run_id]}.{current_dotted}"
        local_map[run_id] = dotted_order

        payload: Dict[str, Any] = {
            "id": run_id,
            "name": run_name,
            "run_type": run_type,
            "project_name": self._project_name,
            "start_time": now.isoformat(),
            "trace_id": effective_trace_id,
            "dotted_order": dotted_order,
        }
        try:
            payload["inputs"] = jsonable(inputs)
        except Exception as exc:  # noqa: BLE001 - mirrors Java's best-effort catch
            logger.warning("Inputs 직렬화 실패: %s", exc)

        if parent_run_id is not None:
            payload["parent_run_id"] = parent_run_id

        await self._send_request_async("POST", _API_URL, payload)
        return run_id

    async def end_trace(self, run_id: str, outputs: Any) -> None:
        payload: Dict[str, Any] = {"end_time": datetime.now(timezone.utc).isoformat()}
        try:
            payload["outputs"] = jsonable(outputs)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Outputs 직렬화 실패: %s", exc)

        await self._send_request_async("PATCH", f"{_API_URL}/{run_id}", payload)
        self._cleanup_local_context(run_id)

    async def error_trace(self, run_id: str, error_message: Optional[str]) -> None:
        payload: Dict[str, Any] = {
            "end_time": datetime.now(timezone.utc).isoformat(),
            "error": error_message,
        }
        await self._send_request_async("PATCH", f"{_API_URL}/{run_id}", payload)
        self._cleanup_local_context(run_id)

    def _cleanup_local_context(self, run_id: str) -> None:
        local_map = self._local_map()
        local_map.pop(run_id, None)
        if not local_map:
            _dotted_order_context.set({})

    async def _send_request_async(self, method: str, url: str, payload: Dict[str, Any]) -> None:
        if self._api_key == _UNSET_API_KEY or not self._api_key:
            return

        try:
            response = await self._client.request(
                method,
                url,
                headers={"x-api-key": self._api_key, "Content-Type": "application/json"},
                json=payload,
            )
            if response.status_code >= 400:
                logger.error("LangSmith API 에러 [%s]: %s", response.status_code, response.text)
        except httpx.HTTPError as exc:
            logger.error("LangSmith 물리적 트레이스 전송 실패 (네트워크 오류 등): %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.error("LangSmith 전송 중 알 수 없는 에러 발생: %s", exc)
