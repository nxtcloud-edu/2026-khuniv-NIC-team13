"""Minimal stand-in for Spring AI's ``PromptTemplate`` ``.param(name, value)``
chaining: replaces literal ``{name}`` placeholders without touching any other
braces in the template (important since JSON schema text is often
interpolated as a param value)."""
from __future__ import annotations

from typing import Any


def render(template: str, **params: Any) -> str:
    result = template
    for key, value in params.items():
        result = result.replace("{" + key + "}", str(value))
    return result
