from unittest.mock import MagicMock

import pytest

from app.config.settings import DynamoDBTables
from app.repository.previous_resume_data_repository import (
    DynamoDbPreviousResumeDataRepository,
)


@pytest.mark.asyncio
async def test_get_resume_text_uses_document_context_table_and_returns_context_text():
    client = MagicMock()
    tables = DynamoDBTables(resume_coordinates="resume-coordinates-table", document_context="document-context-table")
    client.get_item.return_value = {"Item": {"context": {"S": "합격자 이력서 내용"}}}

    repo = DynamoDbPreviousResumeDataRepository(client, tables)

    result = await repo.get_resume_text("resume-1")

    assert result == "합격자 이력서 내용"
    client.get_item.assert_called_once()
    _, kwargs = client.get_item.call_args
    assert kwargs["TableName"] == "document-context-table"


@pytest.mark.asyncio
async def test_get_score_by_track_uses_resume_coordinates_table():
    client = MagicMock()
    tables = DynamoDBTables(resume_coordinates="resume-coordinates-table", document_context="document-context-table")
    client.scan.return_value = {
        "Items": [
            {
                "company": {"S": "회사"},
                "position": {"S": "직무"},
                "track": {"S": "engineering"},
                "x": {"N": "4.0"},
                "y": {"N": "3.8"},
                "z": {"N": "4.2"},
            }
        ]
    }

    repo = DynamoDbPreviousResumeDataRepository(client, tables)

    result = await repo.get_score_by_track("engineering")

    assert result is not None
    client.scan.assert_called_once()
    _, kwargs = client.scan.call_args
    assert kwargs["TableName"] == "resume-coordinates-table"
    assert kwargs["ExpressionAttributeNames"] == {"#track": "track"}


@pytest.mark.asyncio
async def test_list_company_track_stats_groups_paginated_rows_and_filters_small_samples():
    client = MagicMock()
    tables = DynamoDBTables(
        resume_coordinates="resume-coordinates-table",
        document_context="document-context-table",
    )
    client.scan.side_effect = [
        {
            "Items": [
                {
                    "company": {"S": "알파"},
                    "position": {"S": "백엔드"},
                    "track": {"S": "engineering"},
                    "x": {"N": "4.0"},
                    "y": {"N": "3.8"},
                    "z": {"N": "4.2"},
                },
                {
                    "company": {"S": "베타"},
                    "position": {"S": "서버"},
                    "track": {"S": "engineering"},
                    "x": {"N": "3.0"},
                    "y": {"N": "3.0"},
                    "z": {"N": "3.0"},
                },
            ],
            "LastEvaluatedKey": {"id": {"S": "page-1"}},
        },
        {
            "Items": [
                {
                    "company": {"S": "알파"},
                    "position": {"S": "플랫폼"},
                    "track": {"S": "engineering"},
                    "x": {"N": "4.4"},
                    "y": {"N": "4.0"},
                    "z": {"N": "4.0"},
                }
            ]
        },
    ]
    repo = DynamoDbPreviousResumeDataRepository(client, tables)

    result = await repo.list_company_track_stats("engineering", minimum_sample_count=2)

    assert len(result) == 1
    assert result[0].company == "알파"
    assert result[0].sample_count == 2
    assert result[0].x == 4.2
    assert result[0].y == 3.9
    assert result[0].z == 4.1
    assert result[0].overall == 4.07
    assert client.scan.call_count == 2
    assert client.scan.call_args_list[1].kwargs["ExclusiveStartKey"] == {
        "id": {"S": "page-1"}
    }


@pytest.mark.asyncio
async def test_get_score_by_track_averages_multiple_rows_and_falls_back_to_computed_overall():
    client = MagicMock()
    tables = DynamoDBTables(resume_coordinates="resume-coordinates-table", document_context="document-context-table")
    client.scan.return_value = {
        "Items": [
            {
                "company": {"S": "회사"},
                "position": {"S": "직무"},
                "track": {"S": "engineering"},
                "x": {"N": "4.0"},
                "y": {"N": "4.0"},
                "z": {"N": "4.0"},
            },
            {
                "company": {"S": "회사"},
                "position": {"S": "직무"},
                "track": {"S": "engineering"},
                "x": {"N": "2.0"},
                "y": {"N": "2.0"},
                "z": {"N": "2.0"},
            },
        ]
    }

    repo = DynamoDbPreviousResumeDataRepository(client, tables)

    result = await repo.get_score_by_track("engineering")

    assert result.x == 3.0
    assert result.y == 3.0
    assert result.z == 3.0
    assert result.overall == 3.0


@pytest.mark.asyncio
async def test_get_resume_text_returns_none_when_item_missing():
    client = MagicMock()
    tables = DynamoDBTables(resume_coordinates="a", document_context="b")
    client.get_item.return_value = {}

    repo = DynamoDbPreviousResumeDataRepository(client, tables)

    assert await repo.get_resume_text("missing") is None


@pytest.mark.asyncio
async def test_scan_returns_none_when_no_rows_matched():
    client = MagicMock()
    tables = DynamoDBTables(resume_coordinates="a", document_context="b")
    client.scan.return_value = {"Items": []}

    repo = DynamoDbPreviousResumeDataRepository(client, tables)

    assert await repo.get_score_by_track("business") is None


@pytest.mark.asyncio
async def test_dynamodb_errors_are_caught_and_return_none():
    client = MagicMock()
    tables = DynamoDBTables(resume_coordinates="a", document_context="b")
    client.get_item.side_effect = RuntimeError("boom")
    client.scan.side_effect = RuntimeError("boom")

    repo = DynamoDbPreviousResumeDataRepository(client, tables)

    assert await repo.get_resume_text("x") is None
    assert await repo.get_score_by_track("business") is None
