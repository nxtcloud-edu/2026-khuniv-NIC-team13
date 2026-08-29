"""Port of the nested records in
``pertineo.agent.workflow.nodes.WebSearchNode`` (``ToolPlan``,
``ToolPlanResponse``, ``TavilySearchResultDto``)."""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel


class ToolPlan(BaseModel):
    tool_type: Literal["web_search"]
    query: str
    purpose: str


class ToolPlanResponse(BaseModel):
    plans: List[ToolPlan]


class SearchResultItem(BaseModel):
    url: str
    content: str


class TavilySearchResultDto(BaseModel):
    answer: str
    items: List[SearchResultItem]
