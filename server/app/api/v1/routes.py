import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Body,
    Cookie,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, EmailStr

from app.core.config import get_settings
from app.schemas.common import error_response, success_response
from app.services.email_delivery import EmailDeliveryError, get_email_delivery
from app.services.setup_data import SETUP_DATA
from app.services.store import store

router = APIRouter()
setup_router = APIRouter(tags=["Setup"])
auth_router = APIRouter(tags=["Auth"])
session_router = APIRouter(tags=["Session"])
parsing_router = APIRouter(tags=["Parsing"])
analysis_router = APIRouter(tags=["Analysis"])
notice_router = APIRouter(tags=["Notice"])
admin_router = APIRouter(tags=["Admin"])

class Agreements(BaseModel):
    termsOfServiceAgreed: bool = False
    privacyCollectionAgreed: bool = False
    privacyPolicyAgreed: bool = False
    thirdPartySharingAgreed: bool = False


class SessionStartRequest(BaseModel):
    email: str
    agreements: Agreements


class EmailVerificationSendRequest(BaseModel):
    email: EmailStr


class EmailVerifyRequest(BaseModel):
    email: EmailStr
    code: str | int


class NoticeCreateRequest(BaseModel):
    title: str
    content: str


class NoticeUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None


def normalize_email(email: str) -> str:
    return email.strip().lower()


def require_member(email: str) -> None:
    settings = get_settings()
    if settings.ALLOW_ALL_EMAILS:
        return
    if email in settings.MEMBER_EMAIL_WHITELIST:
        return
    if any(email.endswith(domain) for domain in settings.ALLOWED_MEMBER_EMAIL_DOMAINS):
        return
    raise HTTPException(status_code=403, detail=error_response("NOT_MEMBER", "경희대학교 구성원이 아니거나 허용된 사용자가 아닙니다."))


def require_email_verified(email: str) -> None:
    if not store.require_verified_email(email):
        raise HTTPException(status_code=400, detail=error_response("EMAIL_NOT_VERIFIED", "이메일 인증이 필요합니다."))


def require_analysis_credit(email: str) -> None:
    if not store.require_credit(email):
        raise HTTPException(status_code=403, detail=error_response("CREDIT_REQUIRED", "분석 가능 횟수가 부족합니다."))


def require_admin_login(login_status: str | None) -> None:
    if login_status != "success":
        raise HTTPException(status_code=403, detail="관리자 로그인이 필요합니다.")


def notice_detail(notice: dict) -> dict:
    return {
        "id": notice["id"],
        "author": "admin",
        "title": notice["title"],
        "content": notice["content"],
        "createdAt": notice["createdAt"],
        "modifiedAt": notice["modifiedAt"],
    }


@setup_router.get("/api/setup/{kind}")
def setup_list(kind: str) -> dict:
    if kind not in SETUP_DATA:
        raise HTTPException(status_code=404, detail=error_response("NOT_FOUND", "setup list not found"))
    return success_response({"items": SETUP_DATA[kind]})


@auth_router.post("/api/auth/email/verification")
def send_verification(request: EmailVerificationSendRequest) -> dict:
    email = normalize_email(str(request.email))
    require_member(email)
    delivery = get_email_delivery()
    code = delivery.create_code()
    try:
        delivery.send_verification_code(email, code)
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=502,
            detail=error_response("EMAIL_SEND_FAILED", "인증 이메일 전송에 실패했습니다."),
        ) from exc
    store.issue_email_code(email, code=code)
    return success_response(None, "인증 번호 발송")


@auth_router.post("/api/auth/email/verify")
def verify_email(request: EmailVerifyRequest) -> dict:
    email = normalize_email(str(request.email))
    require_member(email)
    code = str(request.code)
    if not code or not store.verify_email_code(email, code):
        raise HTTPException(status_code=400, detail=error_response("EMAIL_VERIFICATION_FAILED", "인증번호가 일치하지 않습니다."))
    return success_response({"email": email, "verified": True})


@auth_router.get("/api/auth/email/credit")
def get_credit(email: str = Query(...)) -> dict:
    normalized = normalize_email(email)
    return success_response(store.get_credit(normalized))


@session_router.post("/api/sessions/start")
def start_session(request: SessionStartRequest, response: Response) -> dict:
    email = normalize_email(request.email)
    require_member(email)
    agreements = request.agreements
    if not all([
        agreements.termsOfServiceAgreed,
        agreements.privacyCollectionAgreed,
        agreements.privacyPolicyAgreed,
        agreements.thirdPartySharingAgreed,
    ]):
        raise HTTPException(status_code=400, detail=error_response("AGREEMENT_REQUIRED", "모든 약관에 동의해야 합니다."))
    require_email_verified(email)
    session = store.issue_session(email, get_settings().SESSION_EXPIRE_MINUTES)
    response.set_cookie(
        get_settings().SESSION_COOKIE_NAME,
        session["sessionId"],
        httponly=True,
        samesite="lax",
        max_age=get_settings().SESSION_EXPIRE_MINUTES * 60,
        path="/",
    )
    return success_response({
        "member": {"email": email},
        "agreements": agreements.model_dump(),
        "expiresAt": session["expiresAt"].isoformat(),
    })


@session_router.post("/api/sessions/extend")
def extend_session(request: Request, response: Response) -> dict:
    settings = get_settings()
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_id:
        raise HTTPException(status_code=400, detail=error_response("INVALID_SESSION", "세션이 유효하지 않습니다."))
    session = store.extend_session(session_id, settings.SESSION_EXTEND_MINUTES)
    if session is None:
        raise HTTPException(status_code=400, detail=error_response("INVALID_SESSION", "세션이 유효하지 않습니다."))
    response.set_cookie(
        settings.SESSION_COOKIE_NAME,
        session_id,
        httponly=True,
        samesite="lax",
        max_age=settings.SESSION_EXTEND_MINUTES * 60,
        path="/",
    )
    return success_response({"status": "ACTIVE", "expiresAt": session["expiresAt"].isoformat()})


@parsing_router.post("/api/parse/convert")
def parse_convert(input_data: str = Body(..., media_type="text/plain")) -> dict:
    text = input_data if isinstance(input_data, str) else str(input_data)
    non_empty = [line.strip() for line in text.splitlines() if line.strip()]
    questions = [line for line in non_empty if line.endswith("?") or line.startswith("Q")]
    answers = [line for line in non_empty if line not in questions]
    if not questions and text.strip():
        questions = ["자기소개서 문항"]
        answers = [text.strip()]
    return success_response({"question_list": questions, "answer_list": answers}, "스마트 파싱 성공")


@analysis_router.post("/api/analysis")
def analysis(request: dict) -> StreamingResponse:
    user_id = normalize_email(str(request.get("userId", "")))
    require_member(user_id)
    require_email_verified(user_id)
    require_analysis_credit(user_id)

    def events():
        event = {
            "id": "analysis-engine-unavailable",
            "type": "evaluate_error",
            "status": "FAILED",
            "data": (
                "현재 FastAPI 서버에는 분석 엔진이 아직 연결되지 않았습니다. "
                "입력 내용과 분석 이용 횟수는 차감되지 않았습니다."
            ),
        }
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@notice_router.post("/api/notice")
def create_notice(request: NoticeCreateRequest) -> dict:
    return success_response(notice_detail(store.create_notice(request.title, request.content)))


@notice_router.get("/api/notice")
def list_notices(page: int = 1, size: int = 10) -> dict:
    safe_page = max(page, 1)
    safe_size = max(size, 1)
    notices, total = store.list_notices(safe_page, safe_size)
    return success_response({
        "notices": [{"id": n["id"], "title": n["title"], "modifiedAt": n["modifiedAt"]} for n in notices],
        "totalElements": total,
        "page": safe_page,
    })


@notice_router.get("/api/notice/{notice_id}")
def get_notice(notice_id: int) -> dict:
    notice = store.get_notice(notice_id)
    if notice is None:
        raise HTTPException(status_code=404, detail=error_response("NOTICE_NOT_FOUND", "공지사항을 찾을 수 없습니다."))
    return success_response(notice_detail(notice))


@notice_router.patch("/api/notice/{notice_id}")
@notice_router.put("/api/notice/{notice_id}")
def update_notice(notice_id: int, request: NoticeUpdateRequest | None = None) -> dict:
    request = request or NoticeUpdateRequest()
    notice = store.update_notice(notice_id, request.title, request.content)
    if notice is None:
        raise HTTPException(status_code=404, detail=error_response("NOTICE_NOT_FOUND", "공지사항을 찾을 수 없습니다."))
    return success_response({"id": notice["id"], "title": notice["title"], "modifiedAt": notice["modifiedAt"]})


@notice_router.delete("/api/notice/{notice_id}")
def delete_notice(notice_id: int) -> dict:
    notice = store.delete_notice(notice_id)
    if notice is None:
        raise HTTPException(status_code=404, detail=error_response("NOTICE_NOT_FOUND", "공지사항을 찾을 수 없습니다."))
    return success_response({"id": notice["id"], "title": notice["title"], "deletedAt": datetime.now(UTC).replace(microsecond=0).isoformat()})


@admin_router.get("/admin", response_class=HTMLResponse)
def admin(loginStatus: str | None = Cookie(default=None)) -> str:
    if loginStatus != "success":
        return "login"
    return "notices"


@admin_router.post("/admin/login", response_class=HTMLResponse)
def admin_login(response: Response, payload: Annotated[dict, Body()]) -> str:
    settings = get_settings()
    if payload.get("username") != settings.admin_username or payload.get("password") != settings.admin_password:
        raise HTTPException(status_code=400, detail="로그인 실패")
    response.set_cookie("loginStatus", "success", max_age=600, path="/", httponly=True, samesite="lax")
    return "notices"


@admin_router.post("/admin/notices", response_class=HTMLResponse)
def admin_notices(loginStatus: str | None = Cookie(default=None)) -> str:
    require_admin_login(loginStatus)
    return "notices"


@admin_router.get("/admin/notices/detail/{notice_id}", response_class=HTMLResponse)
def admin_notice_detail(notice_id: int, loginStatus: str | None = Cookie(default=None)) -> str:
    require_admin_login(loginStatus)
    return "notice-detail"


@admin_router.get("/admin/notices/edit/{notice_id}", response_class=HTMLResponse)
def admin_notice_edit(notice_id: int, loginStatus: str | None = Cookie(default=None)) -> str:
    require_admin_login(loginStatus)
    return "notice-edit"


@admin_router.post("/admin/notices/edit/{notice_id}", response_class=HTMLResponse)
def admin_notice_edit_save(
    notice_id: int,
    title: str = Form(...),
    content: str = Form(...),
    loginStatus: str | None = Cookie(default=None),
) -> str:
    require_admin_login(loginStatus)
    store.update_notice(notice_id, title, content)
    return f"redirect:/admin/notices/detail/{notice_id}"


@admin_router.post("/admin/notices/delete/{notice_id}", response_class=HTMLResponse)
def admin_notice_delete(notice_id: int, loginStatus: str | None = Cookie(default=None)) -> str:
    require_admin_login(loginStatus)
    store.delete_notice(notice_id)
    return "redirect:/admin"


@admin_router.get("/admin/notices/form", response_class=HTMLResponse)
def admin_notice_form(loginStatus: str | None = Cookie(default=None)) -> str:
    require_admin_login(loginStatus)
    return "notice-form"


@admin_router.post("/admin/notices/form", response_class=HTMLResponse)
def admin_notice_form_save(
    title: str = Form(...),
    content: str = Form(...),
    loginStatus: str | None = Cookie(default=None),
) -> str:
    require_admin_login(loginStatus)
    notice = store.create_notice(title, content)
    return f"redirect:/admin/notices/detail/{notice['id']}"


@admin_router.get("/admin/popup/form", response_class=HTMLResponse)
def popup_form(loginStatus: str | None = Cookie(default=None)) -> str:
    require_admin_login(loginStatus)
    return "popup-form"


@admin_router.get("/admin/popup/image")
def popup_image() -> Response:
    if not store.popup or not store.popup.get("image"):
        raise HTTPException(status_code=404, detail="popup image not found")
    return Response(content=store.popup["image"], media_type="image/png")


@admin_router.post("/admin/popup/form", response_class=HTMLResponse)
async def post_popup(
    image: Annotated[UploadFile, File()],
    title: str = Form(...),
    link: str = Form(""),
    loginStatus: str | None = Cookie(default=None),
) -> str:
    require_admin_login(loginStatus)
    store.popup = {"title": title, "link": link, "image": await image.read()}
    return "redirect:/admin/popup/form"


@admin_router.get("/admin/logs/{date}", response_class=HTMLResponse)
def admin_logs(date: str, loginStatus: str | None = Cookie(default=None)) -> str:
    require_admin_login(loginStatus)
    return "logs"


router.include_router(setup_router)
router.include_router(auth_router)
router.include_router(session_router)
router.include_router(parsing_router)
router.include_router(analysis_router)
router.include_router(notice_router)
router.include_router(admin_router)
