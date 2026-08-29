"""Port of ``pertineo.agent.workflow.nodes.ReviserNode.RevisedAnswerInfo``."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel


class RevisedAnswerInfo(BaseModel):
    best_reply: List[str]
    reply_reason: List[str]
    expectation: List[str]


class SingleRevisedAnswer(BaseModel):
    best_reply: str
    reply_reason: str
    expectation: str
