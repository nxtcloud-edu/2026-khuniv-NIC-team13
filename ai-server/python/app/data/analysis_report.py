"""Port of ``pertineo.agent.data.AnalysisReport`` and its nested records.

Top-level DTO describing the final AI analysis/evaluation report shape used
by downstream consumers (e.g. the frontend contract / report.json fixture).
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class ScoreData(BaseModel):
    x: int
    y: int
    z: int


class CategoryListData(BaseModel):
    x: List[str]
    y: List[str]
    z: List[str]


class CategoryStringData(BaseModel):
    x: str
    y: str
    z: str


class CompareAnalysisData(BaseModel):
    x: str
    y: str
    z: str
    overall: str


class ExecutionData(BaseModel):
    title: str
    method: str
    execution: str
    background: str
    purpose: str


class ImproveStrategyData(BaseModel):
    method: str
    execution: List[ExecutionData]
    expectation: str


class AnalysisReport(BaseModel):
    level: str
    job_summary: str
    my_score: ScoreData
    pass_score: ScoreData
    overall: str
    criterion: CategoryListData
    basis: CategoryListData
    role_fit: str
    domain_fit: str
    culture_fit: str
    skill_fit: str
    score_summary: List[str]
    compare_analysis: CompareAnalysisData
    referenced_count: int
    compare_prob: List[str]
    strength: List[str]
    weakness: List[str]
    advice: List[str]
    improve_strategy: ImproveStrategyData
    revised_reply: List[str]
    revised_basis: List[str]
    expectation: List[str]
    revised_score: ScoreData
    improved_basis: CategoryStringData

    model_config = {
        "populate_by_name": True,
        "alias_generator": lambda field_name: {
            "job_summary": "jobSummary",
            "my_score": "myScore",
            "pass_score": "passScore",
            "role_fit": "roleFit",
            "domain_fit": "domainFit",
            "culture_fit": "cultureFit",
            "skill_fit": "skillFit",
            "score_summary": "scoreSummary",
            "compare_analysis": "compareAnalysis",
            "referenced_count": "referencedCount",
            "compare_prob": "compareProb",
            "improve_strategy": "improveStrategy",
            "revised_reply": "revisedReply",
            "revised_basis": "revisedBasis",
            "revised_score": "revisedScore",
            "improved_basis": "improvedBasis",
        }.get(field_name, field_name),
    }
