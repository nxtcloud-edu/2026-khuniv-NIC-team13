"""Port of ``pertineo.agent.repository.PreviousAnalysisResult`` /
``CompareAnalysisData``."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class PreviousAnalysisResult(BaseModel):
    company: Optional[str] = None
    position: Optional[str] = None
    track: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    overall: Optional[float] = None


class CompareAnalysisData(BaseModel):
    """Research-time identification entity; ``id`` is not used as a key."""

    company: Optional[str] = None
    position: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    id: Optional[str] = None


class HistoricalCompanyStats(BaseModel):
    """Aggregated score baseline for one company and one career track."""

    company: str
    track: str
    sample_count: int
    x: float
    y: float
    z: float
    overall: float
