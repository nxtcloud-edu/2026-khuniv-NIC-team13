from io import BytesIO
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.controllers.parse_controller import router
from app.service.smart_parsing_models import ParseResult


class FakeResumeFileParsingService:
    async def parse(self, upload):
        assert upload.filename == "resume.pdf"
        assert await upload.read() == b"%PDF"
        return ParseResult(
            question_list=["대학교명", "전공"],
            answer_list=["경희대학교", "컴퓨터공학"],
        )


def test_parse_file_route_returns_main_server_contract():
    app = FastAPI()
    app.include_router(router)
    app.state.container = SimpleNamespace(
        resume_file_parsing_service=FakeResumeFileParsingService()
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/parse/file",
            files={"file": ("resume.pdf", BytesIO(b"%PDF"), "application/pdf")},
        )

    assert response.status_code == 200
    assert response.json() == {
        "question_list": ["대학교명", "전공"],
        "answer_list": ["경희대학교", "컴퓨터공학"],
    }
