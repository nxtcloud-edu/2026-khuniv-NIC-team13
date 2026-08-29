"""Port of ``pertineo.agent.workflow.track.Track``."""
from __future__ import annotations

import re
from enum import Enum

_BUSINESS_TOKEN = re.compile(r"\bbusiness\b")
_ENGINEERING_TOKEN = re.compile(r"\bengineering\b")


class Track(str, Enum):
    BUSINESS = "business"
    ENGINEERING = "engineering"

    def persistence_value(self) -> str:
        return self.value

    @staticmethod
    def parse(raw_track: str | None) -> "Track":
        if raw_track is None or not raw_track.strip():
            raise ValueError("track must not be blank")

        normalized = raw_track.strip().lower()
        if normalized == Track.BUSINESS.value:
            return Track.BUSINESS
        if normalized == Track.ENGINEERING.value:
            return Track.ENGINEERING

        contains_business = _BUSINESS_TOKEN.search(normalized) is not None
        contains_engineering = _ENGINEERING_TOKEN.search(normalized) is not None
        if contains_business and not contains_engineering:
            return Track.BUSINESS
        if contains_engineering and not contains_business:
            return Track.ENGINEERING

        raise ValueError(f"unknown track: {raw_track}")
