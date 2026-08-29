"""Port of ``pertineo.agent.workflow.nodes.DataNode``."""
from __future__ import annotations

from app.repository.previous_resume_data_repository import PreviousResumeDataRepository
from app.workflow.event import WorkflowEventSink
from app.workflow.nodes.base import AgentNode
from app.workflow.state import AgentState
from app.workflow.track import Track


class DataNode(AgentNode):
    def __init__(self, previous_resume_data_repository: PreviousResumeDataRepository) -> None:
        self._previous_resume_data_repository = previous_resume_data_repository

    async def execute(self, events: WorkflowEventSink, state: AgentState) -> AgentState:
        track = Track.parse(state.track).persistence_value()

        try:
            score = await self._previous_resume_data_repository.get_score_by_company_and_track(
                state.company or "", track
            )
            if score is not None:
                state.context_db = score

            if state.context_db is not None:
                await events.running("pass_score", state.context_db)
            else:
                score_by_track = await self._previous_resume_data_repository.get_score_by_track(track)
                if score_by_track is not None:
                    state.context_db = score_by_track
                await events.running(
                    "pass_score_none", "부합하는 데이터가 충분하지 않아, 동일 직군 데이터를 활용합니다."
                )
                await events.running("pass_score", state.context_db)
        except Exception as exc:  # noqa: BLE001
            await events.failed("data_node_error", "데이터 참조에 실패했습니다.")
            raise RuntimeError("데이터 참조에 실패했습니다.") from exc

        return state

    def decide_next_node(self, state: AgentState) -> str:
        return "EVALUATE"
