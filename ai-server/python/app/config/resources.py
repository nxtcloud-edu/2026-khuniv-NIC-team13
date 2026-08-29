"""Classpath-resource-style loading, mirroring Spring's ``ClassPathResource``.

All prompt/data files live under ``python/resources`` (copied verbatim from
``src/main/resources``), so any relative path used in the original
``@Value("classpath:/...")`` annotations maps 1:1 to a path here.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.config.settings import get_settings


def resource_path(*parts: str) -> Path:
    return Path(get_settings().resources_dir).joinpath(*parts)


def read_text(*parts: str, encoding: str = "utf-8") -> str:
    return resource_path(*parts).read_text(encoding=encoding)


def read_json(*parts: str) -> dict:
    return json.loads(resource_path(*parts).read_text(encoding="utf-8"))


def resource_exists(*parts: str) -> bool:
    return resource_path(*parts).exists()
