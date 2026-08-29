from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import UploadFile

from app.service.resume_file_parsing import (
    EmptyResumeFileError,
    OpenAiResumeFileParser,
    ResumeFileParsingService,
    ResumeFileTooLargeError,
    UnsupportedResumeFileError,
)
from app.service.smart_parsing_models import ParseResult


class FakeResumeFileParser:
    def __init__(self) -> None:
        self.call = None

    async def parse(self, *, filename, content_type, content):
        self.call = (filename, content_type, content)
        return ParseResult(
            question_list=["대학교명", "전공", "학점"],
            answer_list=["경희대학교", "소프트웨어융합학과", "4.1"],
        )


def upload(content: bytes, filename: str = "original.pdf", content_type: str = "application/pdf") -> UploadFile:
    return UploadFile(BytesIO(content), filename=filename, headers={"content-type": content_type})


@pytest.mark.asyncio
async def test_parse_validates_and_forwards_pdf_with_safe_filename():
    parser = FakeResumeFileParser()
    service = ResumeFileParsingService(parser)

    result = await service.parse(upload(b"%PDF-1.7 resume"))

    assert result.question_list == ["대학교명", "전공", "학점"]
    assert parser.call == ("resume.pdf", "application/pdf", b"%PDF-1.7 resume")


@pytest.mark.asyncio
async def test_parse_rejects_empty_file():
    with pytest.raises(EmptyResumeFileError):
        await ResumeFileParsingService(FakeResumeFileParser()).parse(upload(b""))


@pytest.mark.asyncio
async def test_parse_rejects_unsupported_file():
    with pytest.raises(UnsupportedResumeFileError):
        await ResumeFileParsingService(FakeResumeFileParser()).parse(
            upload(b"resume", "resume.hwp", "application/x-hwp")
        )


@pytest.mark.asyncio
async def test_parse_rejects_file_above_limit():
    with pytest.raises(ResumeFileTooLargeError):
        await ResumeFileParsingService(FakeResumeFileParser(), max_bytes=5).parse(upload(b"123456"))


@pytest.mark.asyncio
async def test_openai_parser_sends_inline_file_and_structured_output_contract():
    captured = {}

    class Responses:
        async def parse(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                output_parsed=ParseResult(
                    question_list=["대학교명"], answer_list=["경희대학교"]
                )
            )

    client = SimpleNamespace(responses=Responses())
    parser = OpenAiResumeFileParser("unused", "gpt-5-mini", client=client)

    result = await parser.parse(
        filename="resume.pdf",
        content_type="application/pdf",
        content=b"%PDF",
    )

    assert result.answer_list == ["경희대학교"]
    assert captured["model"] == "gpt-5-mini"
    assert captured["text_format"] is ParseResult
    assert captured["store"] is False
    file_input = captured["input"][0]["content"][0]
    assert file_input["filename"] == "resume.pdf"
    assert file_input["file_data"] == "data:application/pdf;base64,JVBERg=="
