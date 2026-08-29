"""Port of ``pertineo.agent.config.SmartParsingProperties``."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SmartParsingProperties:
    primary_model: str = "gpt-5-nano"
    fallback_model: str = "gpt-5-mini"
    fallback_enabled: bool = True
    fallback_max_chars: int = 1000
