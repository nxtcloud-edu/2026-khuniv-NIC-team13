from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.repositories.protocols import isoformat_utc


class InMemoryRepository:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.notices: dict[int, dict] = {}
        self.next_notice_id = 1
        self.sessions: dict[str, dict] = {}
        self.email_codes: dict[str, str] = {}
        self.email_code_expires_at: dict[str, datetime] = {}
        self.email_verified: set[str] = set()
        self.email_credit: dict[str, dict] = {}
        self.popup: dict | None = None
        self.create_notice("Welcome", "Pertineo notice")

    def create_notice(self, title: str, content: str) -> dict:
        now = isoformat_utc(datetime.now(UTC))
        notice = {"id": self.next_notice_id, "title": title, "content": content, "createdAt": now, "modifiedAt": now}
        self.notices[self.next_notice_id] = notice
        self.next_notice_id += 1
        return notice

    def list_notices(self, page: int, size: int) -> tuple[list[dict], int]:
        notices = sorted(self.notices.values(), key=lambda x: x["id"], reverse=True)
        start = max(page - 1, 0) * size
        return notices[start : start + size], len(notices)

    def get_notice(self, notice_id: int) -> dict | None:
        return self.notices.get(notice_id)

    def update_notice(self, notice_id: int, title: str | None, content: str | None) -> dict | None:
        notice = self.notices.get(notice_id)
        if notice is None:
            return None
        if title is not None:
            notice["title"] = title
        if content is not None:
            notice["content"] = content
        notice["modifiedAt"] = isoformat_utc(datetime.now(UTC))
        return notice

    def delete_notice(self, notice_id: int) -> dict | None:
        return self.notices.pop(notice_id, None)

    def issue_email_code(self, email: str, code: str = "123456", ttl_minutes: int = 5) -> None:
        self.email_codes[email] = code
        self.email_code_expires_at[email] = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
        self.email_credit.setdefault(email, {"email": email, "remainCount": 3, "verified": False})

    def verify_email_code(self, email: str, code: str) -> bool:
        expected = self.email_codes.get(email)
        expires_at = self.email_code_expires_at.get(email)
        if expected is None or expires_at is None or expires_at < datetime.now(UTC):
            return False
        if expected != code:
            return False
        self.email_codes.pop(email, None)
        self.email_code_expires_at.pop(email, None)
        self.email_verified.add(email)
        credit = self.email_credit.setdefault(email, {"email": email, "remainCount": 3, "verified": True})
        credit["verified"] = True
        return True

    def require_verified_email(self, email: str) -> bool:
        return email in self.email_verified

    def get_credit(self, email: str) -> dict:
        return self.email_credit.setdefault(email, {"email": email, "remainCount": 3, "verified": email in self.email_verified})

    def require_credit(self, email: str) -> bool:
        credit = self.email_credit.setdefault(email, {"email": email, "remainCount": 0, "verified": email in self.email_verified})
        return bool(credit.get("verified")) and int(credit.get("remainCount", 0)) > 0

    def consume_credit(self, email: str) -> dict:
        credit = self.email_credit.setdefault(email, {"email": email, "remainCount": 0, "verified": email in self.email_verified})
        credit["remainCount"] = max(int(credit.get("remainCount", 0)) - 1, 0)
        return credit

    def issue_session(self, email: str, minutes: int) -> dict:
        session_id = str(uuid4())
        expires_at = datetime.now(UTC) + timedelta(minutes=minutes)
        self.sessions[session_id] = {"email": email, "expiresAt": expires_at}
        return {"sessionId": session_id, "expiresAt": expires_at}

    def extend_session(self, session_id: str, minutes: int) -> dict | None:
        session = self.sessions.get(session_id)
        if session is None or session["expiresAt"] < datetime.now(UTC):
            return None
        session["expiresAt"] = datetime.now(UTC) + timedelta(minutes=minutes)
        return session


store = InMemoryRepository()
