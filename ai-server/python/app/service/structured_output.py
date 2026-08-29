"""Stand-in for Spring AI's ``BeanOutputConverter.getFormat()`` — produces
JSON-schema format instructions to interpolate into a ``{format}``
placeholder in a prompt template."""
from __future__ import annotations

import json
from typing import Type

from pydantic import BaseModel


def json_schema_format_instructions(model: Type[BaseModel]) -> str:
    schema = json.dumps(model.model_json_schema(), ensure_ascii=False)
    return (
        "Your response should be in JSON format. "
        "Do not include any explanations, only provide a RFC8259 compliant JSON response "
        "following this format without deviation. "
        "Do not include markdown code blocks in your response. "
        f"Here is the JSON Schema instance your output must adhere to:\n{schema}"
    )
