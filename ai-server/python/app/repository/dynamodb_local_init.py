"""Port of ``pertineo.agent.DynamoDBLocalTableInitializer``.

Only runs when the active profile is ``local`` (mirrors the Java
``@Profile("local")`` guard). Creates the tables the app needs against
DynamoDB Local and seeds them with ``data_dummy.json`` if empty. Failures
are logged and swallowed — the app must still start if DynamoDB Local isn't
running.
"""
from __future__ import annotations

import asyncio
import json
import logging
from decimal import Decimal
from typing import Any, Dict, List

from botocore.exceptions import ClientError

from app.config.resources import read_json, resource_exists
from app.config.settings import DynamoDBTables

logger = logging.getLogger(__name__)


def initialize_tables_sync(dynamodb_client: Any, tables: DynamoDBTables) -> None:
    try:
        if not _is_dynamodb_local_running(dynamodb_client):
            logger.warning("===========================================")
            logger.warning("DynamoDB Local이 실행 중이 아닙니다!")
            logger.warning("테이블 자동 생성을 건너뜁니다.")
            logger.warning("")
            logger.warning("DynamoDB Local 시작 방법:")
            logger.warning("  docker-compose up dynamodb-local -d")
            logger.warning("===========================================")
            return

        logger.info("DynamoDB Local 테이블 초기화 시작...")
        _create_all_tables(dynamodb_client, tables)
        _seed_dummy_data_if_empty(dynamodb_client, tables)
        logger.info("DynamoDB Local 테이블 초기화 완료")
    except Exception as exc:  # noqa: BLE001
        logger.warning("테이블 초기화 실패: %s - 애플리케이션은 계속 실행됩니다.", exc)


async def initialize_tables(dynamodb_client: Any, tables: DynamoDBTables) -> None:
    await asyncio.to_thread(initialize_tables_sync, dynamodb_client, tables)


def _is_dynamodb_local_running(client: Any) -> bool:
    try:
        client.list_tables(Limit=1)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.debug("DynamoDB Local 연결 실패: %s", exc)
        return False


def _create_all_tables(client: Any, tables: DynamoDBTables) -> None:
    logger.info("로컬 테이블 생성 시작...")
    for table_name in (tables.resume_coordinates, tables.document_context):
        _create_table_if_not_exists(client, table_name)
    logger.info("로컬 테이블 생성 완료")


def _create_table_if_not_exists(client: Any, table_name: str) -> None:
    try:
        client.describe_table(TableName=table_name)
        logger.debug("테이블 이미 존재: %s", table_name)
        return
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceNotFoundException":
            logger.warning("테이블 상태 확인 실패: %s - %s", table_name, exc)
            return
    except Exception as exc:  # noqa: BLE001
        logger.warning("테이블 상태 확인 실패: %s - %s", table_name, exc)
        return

    try:
        client.create_table(
            TableName=table_name,
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        logger.info("테이블 생성됨: %s", table_name)
        _wait_for_table_to_be_active(client, table_name)
    except Exception as exc:  # noqa: BLE001
        logger.error("테이블 생성 실패: %s - %s", table_name, exc)


def _wait_for_table_to_be_active(client: Any, table_name: str) -> None:
    import time

    max_retries = 30
    for _ in range(max_retries):
        try:
            response = client.describe_table(TableName=table_name)
            if response["Table"]["TableStatus"] == "ACTIVE":
                logger.debug("테이블 활성화 완료: %s", table_name)
                return
            time.sleep(1)
        except Exception as exc:  # noqa: BLE001
            logger.warning("테이블 상태 확인 중 오류: %s - %s", table_name, exc)
            return
    logger.warning("테이블 활성화 대기 시간 초과: %s", table_name)


def _seed_dummy_data_if_empty(client: Any, tables: DynamoDBTables) -> None:
    table_name = tables.resume_coordinates

    try:
        response = client.scan(TableName=table_name, Select="COUNT", Limit=1)
        if response.get("Count", 0) > 0:
            logger.info("더미 데이터 시딩 건너뜀 (이미 데이터 존재): table=%s, count>0", table_name)
            return
    except Exception as exc:  # noqa: BLE001
        logger.warning("더미 데이터 시딩 전 테이블 조회 실패. 시딩을 건너뜁니다: %s", exc)
        return

    if not resource_exists("data_dummy.json"):
        logger.warning("data_dummy.json이 classpath에 없습니다. 시딩을 건너뜁니다.")
        return

    try:
        rows: List[Dict[str, Any]] = read_json("data_dummy.json")
        writes = [{"PutRequest": {"Item": _to_resume_coordinate_item(row)}} for row in rows]

        batch_size = 25
        for i in range(0, len(writes), batch_size):
            batch = writes[i : i + batch_size]
            client.batch_write_item(RequestItems={table_name: batch})

        logger.info("더미 데이터 시딩 완료: table=%s, count=%s", table_name, len(writes))
    except Exception as exc:  # noqa: BLE001
        logger.warning("더미 데이터 시딩 실패: %s - 애플리케이션은 계속 실행됩니다.", exc)


def _to_resume_coordinate_item(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": {"S": str(row.get("id"))},
        "company": {"S": str(row.get("company"))},
        "position": {"S": str(row.get("position"))},
        "x": {"N": _to_number_string(row.get("x"))},
        "y": {"N": _to_number_string(row.get("y"))},
        "z": {"N": _to_number_string(row.get("z"))},
    }


def _to_number_string(value: Any) -> str:
    if value is None:
        return "0"
    return str(Decimal(str(value)).normalize())
