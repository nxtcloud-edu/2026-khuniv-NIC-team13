"""Port of ``pertineo.agent.workflow.nodes.WebSearchNode``."""
from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

import httpx
from openai import AsyncOpenAI

from app.cache.models import CachedTavilyData
from app.cache.web_search_cache import WebSearchCache
from app.config.resources import read_json
from app.config.settings import get_settings
from app.service.openai_chat_client import OPENAI_FAST, create_openai_client, parse_structured
from app.service.structured_output import json_schema_format_instructions
from app.util.template import render
from app.workflow.event import WorkflowEventSink
from app.workflow.nodes.base import AgentNode
from app.workflow.nodes.websearch_models import (
    SearchResultItem,
    TavilySearchResultDto,
    ToolPlan,
    ToolPlanResponse,
)
from app.workflow.state import AgentState

logger = logging.getLogger(__name__)

_TAVILY_URL = "https://api.tavily.com/search"


class WebSearchNode(AgentNode):
    def __init__(
        self,
        web_search_cache: WebSearchCache,
        client: Optional[AsyncOpenAI] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._client = client or create_openai_client()
        self._http_client = http_client or httpx.AsyncClient(timeout=30.0)
        self._web_search_cache = web_search_cache
        self._settings = get_settings()

    async def check_cache_and_send_sse(self, events: WorkflowEventSink, state: AgentState) -> bool:
        cached_data = self._web_search_cache.cache_retrieve(state.job_position or "", state.company or "")
        if cached_data is not None:
            state.context_web = self._build_context_string_from_cache(cached_data)

            await events.running("web_search_cache_hit", "캐시된 웹 검색 결과를 사용합니다.")
            await events.running("web_search_plan_generated", cached_data.generated_tool_plan)
            for plan, result in zip(cached_data.generated_tool_plan, cached_data.search_result):
                await events.running("web_search_query", plan)
                await events.running("web_search_result", result)
            await events.running("web_search_end", "웹 검색을 완료했습니다. (캐시 사용)")
            return True
        return False

    async def execute(self, events: WorkflowEventSink, state: AgentState) -> AgentState:
        await events.running("web_search_start", "웹 검색을 시작합니다.")

        if await self.check_cache_and_send_sse(events, state):
            return state

        prompts = read_json("prompts", "websearch.json")["prompts"]
        system_template = prompts["system"] + "\n\n{format}"

        await events.running("web_search_planning", "검색 쿼리를 생성중입니다...")
        system_prompt = render(
            system_template,
            job_field=state.job_field or "",
            job_position=state.job_position or "",
            company=state.company or "",
            division=state.division or "",
            date=date.today().isoformat(),
            format=json_schema_format_instructions(ToolPlanResponse),
        )

        plan_response = await parse_structured(
            self._client,
            system_prompt,
            "회사와 직무에 필요한 검색 계획을 생성하세요.",
            ToolPlanResponse,
            options=OPENAI_FAST,
        )

        if plan_response is None or not plan_response.plans:
            await events.failed("web_search_error", "검색 계획 생성에 실패했습니다.")
            raise RuntimeError("검색 계획(ToolPlan)을 생성하지 못했습니다.")

        await events.running("web_search_plan_generated", plan_response.plans)

        web_context_lines = ["=== Web Search Context ==="]
        search_results: List[TavilySearchResultDto] = []

        for plan in plan_response.plans:
            if plan.tool_type != "web_search":
                continue

            await events.running("web_search_query", plan)

            search_result = await self._perform_tavily_search(plan.query)
            search_results.append(search_result)
            await events.running("web_search_result", search_result)

            web_context_lines.append(f"Query: {plan.query}")
            web_context_lines.append(f"Result: {search_result}\n")

        state.context_web = "\n".join(web_context_lines)

        data_to_cache = CachedTavilyData(generated_tool_plan=plan_response.plans, search_result=search_results)
        self._web_search_cache.cache_store(state.job_position or "", state.company or "", data_to_cache)

        await events.running("web_search_end", "웹 검색을 완료했습니다.")
        return state

    async def _perform_tavily_search(self, query: str) -> TavilySearchResultDto:
        try:
            response = await self._http_client.post(
                _TAVILY_URL,
                headers={"Content-Type": "application/json"},
                json={
                    "api_key": self._settings.tavily_api_key,
                    "query": query,
                    "include_answer": True,
                    "max_results": 3,
                },
            )
            response.raise_for_status()
            payload = response.json()

            answer = payload.get("answer") or ""
            items = [
                SearchResultItem(
                    url=result.get("url", "URL 없음"),
                    content=result.get("content", "내용 없음"),
                )
                for result in payload.get("results") or []
            ]
            return TavilySearchResultDto(answer=answer, items=items)
        except Exception:  # noqa: BLE001
            logger.exception("Tavily search failed")
            return TavilySearchResultDto(answer="검색 중 오류가 발생하여 데이터를 가져오지 못했습니다.", items=[])

    def _build_context_string_from_cache(self, cached_data: CachedTavilyData) -> str:
        lines = ["=== Web Search Context (from Cache) ==="]
        for plan, result in zip(cached_data.generated_tool_plan, cached_data.search_result):
            lines.append(f"Query: {plan.query}")
            lines.append(f"Result: {result}\n")
        return "\n".join(lines)

    def decide_next_node(self, state: AgentState) -> str:
        return "DATA"
