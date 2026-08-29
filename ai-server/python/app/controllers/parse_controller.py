"""Port of ``pertineo.agent.controller.ParseController``."""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.service.smart_parsing_models import ParseResult
from app.service.resume_file_parsing import (
    EmptyResumeFileError,
    ResumeFileTooLargeError,
    UnsupportedResumeFileError,
)

router = APIRouter(prefix="/api/parse", tags=["parse"])


@router.post("/convert", response_model=ParseResult)
async def parse_resume(request: Request) -> ParseResult:
    container = request.app.state.container
    raw_body = await request.body()
    input_data = raw_body.decode("utf-8")
    return await container.smart_parsing_service.parse_resume(input_data)


@router.post("/file", response_model=ParseResult)
async def parse_resume_file(request: Request, file: UploadFile = File(...)) -> ParseResult:
    service = request.app.state.container.resume_file_parsing_service
    try:
        return await service.parse(file)
    except EmptyResumeFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file") from exc
    except ResumeFileTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="File too large") from exc
    except UnsupportedResumeFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type",
        ) from exc
