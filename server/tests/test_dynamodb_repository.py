import boto3
from moto import mock_aws

from app.repositories.dynamodb import DynamoDBRepository, create_required_tables


@mock_aws
def test_dynamodb_repository_notice_crud_and_email_session_credit_flow():
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-2")
    create_required_tables(dynamodb)
    repo = DynamoDBRepository(dynamodb)

    notice = repo.create_notice("제목", "내용")
    assert notice["id"] == 1
    counter = repo.counters.get_item(Key={"name": "notice"}).get("Item")
    assert int(counter["value"]) == 1
    assert repo.get_notice(1)["title"] == "제목"
    listed, total = repo.list_notices(page=1, size=10)
    assert total == 1
    assert listed[0]["content"] == "내용"
    assert repo.update_notice(1, "수정", None)["title"] == "수정"
    assert repo.delete_notice(1)["id"] == 1
    assert repo.get_notice(1) is None

    email = "student@khu.ac.kr"
    assert repo.verify_email_code(email, "123456") is False
    repo.issue_email_code(email)
    email_state = repo.emails.get_item(Key={"email": email}).get("Item")
    verification_state = repo.email_verifications.get_item(Key={"email": email}).get("Item")
    assert email_state is None or "accessCode" not in email_state
    assert verification_state["accessCode"] == "123456"
    assert repo.verify_email_code(email, "000000") is False
    assert repo.verify_email_code(email, "123456") is True
    assert repo.require_verified_email(email) is True
    assert repo.require_credit(email) is True
    before = repo.get_credit(email)["remainCount"]
    after = repo.consume_credit(email)["remainCount"]
    assert after == before - 1

    session = repo.issue_session(email, minutes=30)
    extended = repo.extend_session(session["sessionId"], minutes=30)
    assert extended is not None
    assert extended["email"] == email


@mock_aws
def test_dynamodb_repository_writes_ttl_epoch_fields_and_rejects_expired_states():
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-2")
    create_required_tables(dynamodb)
    repo = DynamoDBRepository(dynamodb)

    email = "ttl@khu.ac.kr"
    repo.issue_email_code(email, ttl_minutes=5)
    verification_item = repo.email_verifications.get_item(Key={"email": email})["Item"]
    assert int(verification_item["expiresAtEpoch"]) > 0
    verification_ttl = dynamodb.meta.client.describe_time_to_live(TableName="pertineo-email-verifications")
    assert verification_ttl["TimeToLiveDescription"]["AttributeName"] == "expiresAtEpoch"

    repo.issue_email_code(email, ttl_minutes=-1)
    assert repo.verify_email_code(email, "123456") is False

    session = repo.issue_session(email, minutes=30)
    session_item = repo.sessions.get_item(Key={"sessionId": session["sessionId"]})["Item"]
    assert int(session_item["expiresAtEpoch"]) > 0
    ttl_description = dynamodb.meta.client.describe_time_to_live(TableName="pertineo-sessions")
    assert ttl_description["TimeToLiveDescription"]["AttributeName"] == "expiresAtEpoch"

    expired = repo.issue_session(email, minutes=-1)
    assert repo.extend_session(expired["sessionId"], minutes=30) is None


@mock_aws
def test_dynamodb_repository_popup_singleton():
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-2")
    create_required_tables(dynamodb)
    repo = DynamoDBRepository(dynamodb)

    assert repo.popup is None
    repo.popup = {"title": "팝업", "link": "https://example.com", "image": b"png"}
    assert repo.popup["title"] == "팝업"
    repo.popup = None
    assert repo.popup is None


@mock_aws
def test_dynamodb_notice_ids_use_counter_not_existing_notice_scan():
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-2")
    create_required_tables(dynamodb)
    repo = DynamoDBRepository(dynamodb)

    first = repo.create_notice("첫 번째", "내용")
    second = repo.create_notice("두 번째", "내용")
    assert [first["id"], second["id"]] == [1, 2]

    repo.delete_notice(2)
    third = repo.create_notice("세 번째", "내용")
    assert third["id"] == 3

    counter = repo.counters.get_item(Key={"name": "notice"})["Item"]
    assert int(counter["value"]) == 3
