"""Extract structured resume fields from uploaded documents."""
from __future__ import annotations

import base64
from typing import Protocol

from fastapi import UploadFile
from openai import AsyncOpenAI

from app.service.smart_parsing_models import ParseResult

_EXTRACTION_PROMPT = """업로드된 한국어 이력서를 읽고 입력 가능한 항목을 추출하라.

question_list에는 아래 라벨 중 문서에서 확인되는 것만 사용하라.
answer_list의 같은 위치에 해당 값을 넣어라.
여러 학력이나 경력이 있으면 관련 라벨을 아래 순서대로 반복한다.

- 대학교명, 전공, 학점, 부전공
- 고용 형태, 근무 기간, 회사명, 부서명, 직책
- 수상 이름, 발급처
- 자격 종류, 발급일
- 어학 종류, 어학 점수

규칙:
- 문서에 없는 값은 추측하거나 생성하지 않는다.
- question_list와 answer_list의 길이는 반드시 같아야 한다.
- 학점은 취득 학점만 반환하고 만점 정보는 제외한다.
- 날짜와 기간은 문서 표기를 유지한다.
- 자기소개서 문장이나 개인정보는 반환하지 않는다.
"""


class ResumeFileParser(Protocol):
    async def parse(self, *, filename: str, content_type: str, content: bytes) -> ParseResult: ...


class OpenAiResumeFileParser:
    def __init__(self, api_key: str, model: str, client: AsyncOpenAI | None = None) -> None:
        self._client = client or AsyncOpenAI(api_key=api_key, max_retries=1, timeout=120.0)
        self._model = model

    async def parse(self, *, filename: str, content_type: str, content: bytes) -> ParseResult:
        encoded = base64.b64encode(content).decode("ascii")
        response = await self._client.responses.parse(
            model=self._model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "filename": filename,
                            "file_data": f"data:{content_type};base64,{encoded}",
                        },
                        {"type": "input_text", "text": _EXTRACTION_PROMPT},
                    ],
                }
            ],
            text_format=ParseResult,
            store=False,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("Resume file parsing returned no structured result")
        return parsed


class ResumeFileParsingService:
    def __init__(self, parser: ResumeFileParser, max_bytes: int = 10 * 1024 * 1024) -> None:
        self._parser = parser
        self._max_bytes = max_bytes

    async def parse(self, upload: UploadFile) -> ParseResult:
        filename = upload.filename or "resume.pdf"
        content_type = (upload.content_type or "").split(";", maxsplit=1)[0].lower()
        extension = "." + filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else ""
        allowed = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
        }
        if extension not in allowed or content_type != allowed[extension]:
            raise UnsupportedResumeFileError

        content = await upload.read(self._max_bytes + 1)
        if not content:
            raise EmptyResumeFileError
        if len(content) > self._max_bytes:
            raise ResumeFileTooLargeError

        safe_filename = f"resume{extension}"
        return await self._parser.parse(
            filename=safe_filename,
            content_type=content_type,
            content=content,
        )


class EmptyResumeFileError(ValueError):
    pass


class ResumeFileTooLargeError(ValueError):
    pass


class UnsupportedResumeFileError(ValueError):
    pass
