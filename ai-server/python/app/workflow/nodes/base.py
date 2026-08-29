"""Port of ``pertineo.agent.workflow.nodes.AgentNode``."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.workflow.event import WorkflowEventSink
from app.workflow.state import AgentState


class AgentNode(ABC):
    @abstractmethod
    async def execute(self, events: WorkflowEventSink, state: AgentState) -> AgentState: ...

    @abstractmethod
    def decide_next_node(self, state: AgentState) -> str: ...
