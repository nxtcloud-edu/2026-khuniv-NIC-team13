from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.repositories.protocols import isoformat_utc


def epoch_seconds(value: datetime) -> int:
    return int(value.timestamp())


class DynamoDBRepository:
    """DynamoDB-backed repository adapter for the current Pertineo domain slice.

    Table layout is intentionally explicit and testable before AWS deployment:

    - notices:        table `notices`, pk `id` (N)
    - email states:   table `emails`, pk `email` (S)
    - sessions:       table `sessions`, pk `sessionId` (S)
    - popup:          table `popups`, pk `id` (S), singleton id `active`

    A single-table design may be introduced later, but separate tables match the legacy domain split
    and are easier to validate during migration.
    """

    def __init__(
        self,
        dynamodb_resource: Any,
        notices_table: str = "pertineo-notices",
        emails_table: str = "pertineo-emails",
        email_verifications_table: str = "pertineo-email-verifications",
        sessions_table: str = "pertineo-sessions",
        popups_table: str = "pertineo-popups",
        counters_table: str = "pertineo-counters",
    ) -> None:
        self.notices = dynamodb_resource.Table(notices_table)
        self.emails = dynamodb_resource.Table(emails_table)
        self.email_verifications = dynamodb_resource.Table(email_verifications_table)
        self.sessions = dynamodb_resource.Table(sessions_table)
        self.popups = dynamodb_resource.Table(popups_table)
        self.counters = dynamodb_resource.Table(counters_table)

    def reset(self) -> None:
        raise NotImplementedError("DynamoDBRepository.reset is test/bootstrap responsibility")

    @property
    def popup(self) -> dict | None:
        response = self.popups.get_item(Key={"id": "active"})
        item = response.get("Item")
        if not item:
            return None
        return {"title": item.get("title", ""), "link": item.get("link", ""), "image": item.get("image")}

    @popup.setter
    def popup(self, value: dict | None) -> None:
        if value is None:
            self.popups.delete_item(Key={"id": "active"})
            return
        self.popups.put_item(
            Item={"id": "active", "title": value.get("title", ""), "link": value.get("link", ""), "image": value.get("image", b"")}
        )

    def create_notice(self, title: str, content: str) -> dict:
        notice_id = self._next_notice_id()
        now = isoformat_utc(datetime.now(UTC))
        item = {"id": notice_id, "title": title, "content": content, "createdAt": now, "modifiedAt": now}
        self.notices.put_item(Item=item)
        return dict(item)

    def list_notices(self, page: int, size: int) -> tuple[list[dict], int]:
        response = self.notices.scan()
        items = sorted(response.get("Items", []), key=lambda x: int(x["id"]), reverse=True)
        start = max(page - 1, 0) * size
        return [self._from_ddb_numbers(item) for item in items[start : start + size]], len(items)

    def get_notice(self, notice_id: int) -> dict | None:
        response = self.notices.get_item(Key={"id": notice_id})
        item = response.get("Item")
        return self._from_ddb_numbers(item) if item else None

    def update_notice(self, notice_id: int, title: str | None, content: str | None) -> dict | None:
        existing = self.get_notice(notice_id)
        if existing is None:
            return None
        if title is not None:
            existing["title"] = title
        if content is not None:
            existing["content"] = content
        existing["modifiedAt"] = isoformat_utc(datetime.now(UTC))
        self.notices.put_item(Item=existing)
        return existing

    def delete_notice(self, notice_id: int) -> dict | None:
        existing = self.get_notice(notice_id)
        if existing is None:
            return None
        self.notices.delete_item(Key={"id": notice_id})
        return existing

    def issue_email_code(self, email: str, code: str = "123456", ttl_minutes: int = 5) -> None:
        expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
        self.emails.put_item(Item=self._email_state_item(email, self.get_credit(email)))
        self.email_verifications.put_item(
            Item={
                "email": email,
                "accessCode": code,
                "accessCodeExpiresAt": isoformat_utc(expires_at),
                "expiresAtEpoch": epoch_seconds(expires_at),
            }
        )

    def verify_email_code(self, email: str, code: str) -> bool:
        response = self.email_verifications.get_item(Key={"email": email})
        item = response.get("Item")
        if not item:
            return False
        expected = item.get("accessCode")
        expires_at_raw = item.get("accessCodeExpiresAt")
        if not expected or not expires_at_raw:
            return False
        expires_at = datetime.fromisoformat(expires_at_raw)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expected != code or expires_at < datetime.now(UTC):
            return False
        self.email_verifications.delete_item(Key={"email": email})
        current = self.get_credit(email)
        current["verified"] = True
        current["remainCount"] = int(current.get("remainCount", 3))
        self.emails.put_item(Item=self._email_state_item(email, current))
        return True

    def require_verified_email(self, email: str) -> bool:
        return bool(self.get_credit(email).get("verified", False))

    def get_credit(self, email: str) -> dict:
        response = self.emails.get_item(Key={"email": email})
        item = response.get("Item")
        if not item:
            return {"email": email, "remainCount": 3, "verified": False}
        return self._from_ddb_numbers({"email": email, "remainCount": item.get("remainCount", 3), "verified": item.get("verified", False)})

    def require_credit(self, email: str) -> bool:
        credit = self.get_credit(email)
        return bool(credit.get("verified")) and int(credit.get("remainCount", 0)) > 0

    def consume_credit(self, email: str) -> dict:
        response = self.emails.get_item(Key={"email": email})
        item = response.get("Item") or {"email": email, "verified": False, "remainCount": 0}
        item["remainCount"] = max(int(item.get("remainCount", 0)) - 1, 0)
        self.emails.put_item(Item=item)
        return self._from_ddb_numbers({"email": email, "remainCount": item["remainCount"], "verified": item.get("verified", False)})

    def issue_session(self, email: str, minutes: int) -> dict:
        session_id = str(uuid4())
        expires_at = datetime.now(UTC) + timedelta(minutes=minutes)
        self.sessions.put_item(
            Item={"sessionId": session_id, "email": email, "expiresAt": isoformat_utc(expires_at), "expiresAtEpoch": epoch_seconds(expires_at)}
        )
        return {"sessionId": session_id, "expiresAt": expires_at}

    def extend_session(self, session_id: str, minutes: int) -> dict | None:
        response = self.sessions.get_item(Key={"sessionId": session_id})
        item = response.get("Item")
        if not item:
            return None
        expires_at = datetime.fromisoformat(item["expiresAt"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            return None
        new_expires_at = datetime.now(UTC) + timedelta(minutes=minutes)
        item["expiresAt"] = isoformat_utc(new_expires_at)
        item["expiresAtEpoch"] = epoch_seconds(new_expires_at)
        self.sessions.put_item(Item=item)
        return {"email": item["email"], "expiresAt": new_expires_at}

    @staticmethod
    def _email_state_item(email: str, state: dict) -> dict:
        return {
            "email": email,
            "verified": bool(state.get("verified", False)),
            "remainCount": int(state.get("remainCount", 3)),
        }

    def _next_notice_id(self) -> int:
        response = self.counters.update_item(
            Key={"name": "notice"},
            UpdateExpression="ADD #value :one",
            ExpressionAttributeNames={"#value": "value"},
            ExpressionAttributeValues={":one": 1},
            ReturnValues="UPDATED_NEW",
        )
        return int(response["Attributes"]["value"])

    @staticmethod
    def _from_ddb_numbers(item: dict | None) -> dict:
        if item is None:
            return {}
        converted = {}
        for key, value in item.items():
            if isinstance(value, Decimal):
                converted[key] = int(value) if value == value.to_integral_value() else float(value)
            else:
                converted[key] = value
        return converted


def enable_time_to_live(dynamodb_resource: Any, table_name: str, attribute_name: str = "expiresAtEpoch") -> None:
    dynamodb_resource.meta.client.update_time_to_live(
        TableName=table_name,
        TimeToLiveSpecification={"Enabled": True, "AttributeName": attribute_name},
    )


def create_required_tables(dynamodb_resource: Any, billing_mode: str = "PAY_PER_REQUEST") -> None:
    existing = set(dynamodb_resource.meta.client.list_tables().get("TableNames", []))

    def create_if_missing(name: str, key_name: str, key_type: str) -> None:
        if name in existing:
            return
        dynamodb_resource.create_table(
            TableName=name,
            KeySchema=[{"AttributeName": key_name, "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": key_name, "AttributeType": key_type}],
            BillingMode=billing_mode,
        ).wait_until_exists()

    create_if_missing("pertineo-notices", "id", "N")
    create_if_missing("pertineo-emails", "email", "S")
    create_if_missing("pertineo-email-verifications", "email", "S")
    enable_time_to_live(dynamodb_resource, "pertineo-email-verifications")
    create_if_missing("pertineo-sessions", "sessionId", "S")
    enable_time_to_live(dynamodb_resource, "pertineo-sessions")
    create_if_missing("pertineo-popups", "id", "S")
    create_if_missing("pertineo-counters", "name", "S")
