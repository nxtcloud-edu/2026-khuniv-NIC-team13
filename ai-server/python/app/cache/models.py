"""Port of ``pertineo.agent.cache.CachedTavilyData``."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from app.workflow.nodes.websearch_models import TavilySearchResultDto, ToolPlan


class CachedTavilyData(BaseModel):
    generated_tool_plan: List[ToolPlan] = Field(alias="web_search_plan_generated")
    search_result: List[TavilySearchResultDto] = Field(alias="web_search_result")

    model_config = {"populate_by_name": True}
