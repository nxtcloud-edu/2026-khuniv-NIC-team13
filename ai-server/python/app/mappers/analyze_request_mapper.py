"""Port of ``pertineo.agent.controller.mapper.AnalyzeRequestMapper``."""
from __future__ import annotations

from app.schemas.analyze_request import AnalyzeRequestDto
from app.workflow.state import AgentState


def to_agent_state(request: AnalyzeRequestDto) -> AgentState:
    return AgentState(
        user_id=request.user_id,
        question_list=request.question_list,
        answer_list=request.answer_list,
        education=request.education,
        gpa=request.gpa,
        major=request.major,
        background_career_award=request.background_career_award,
        linguistic_ability=request.linguistic_ability,
        certificates=request.certificates,
        company=request.company,
        job_position=request.job_position,
        job_field=request.job_field,
        division=request.division,
        apply_url=request.apply_url,
    )
