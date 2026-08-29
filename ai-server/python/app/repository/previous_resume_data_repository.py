"""Port of ``pertineo.agent.repository.PreviousResumeDataRepository`` /
``DynamoDbPreviousResumeDataRepository``."""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional

from app.config.settings import DynamoDBTables
from app.repository.models import HistoricalCompanyStats, PreviousAnalysisResult

logger = logging.getLogger(__name__)


class PreviousResumeDataRepository(ABC):
    @abstractmethod
    async def get_score_by_company_and_track(
        self, company: str, track: str
    ) -> Optional[PreviousAnalysisResult]: ...

    @abstractmethod
    async def get_score_by_track(self, track: str) -> Optional[PreviousAnalysisResult]: ...

    @abstractmethod
    async def list_company_track_stats(
        self, track: str, minimum_sample_count: int
    ) -> List[HistoricalCompanyStats]: ...

    @abstractmethod
    async def get_resume_text(self, id_: str) -> Optional[str]: ...


class DynamoDbPreviousResumeDataRepository(PreviousResumeDataRepository):
    """boto3-backed implementation. boto3 calls are synchronous, so they are
    offloaded to a thread via ``asyncio.to_thread`` to keep the FastAPI event
    loop unblocked — the async equivalent of Spring's blocking DynamoDB SDK
    call running off the request thread."""

    def __init__(self, dynamodb_client: Any, tables: DynamoDBTables) -> None:
        self._client = dynamodb_client
        self._tables = tables

    async def get_score_by_company_and_track(
        self, company: str, track: str
    ) -> Optional[PreviousAnalysisResult]:
        return await asyncio.to_thread(
            self._scan_average_sync,
            "#company = :company AND #track = :track",
            {
                ":company": {"S": company},
                ":track": {"S": track},
            },
        )

    async def get_score_by_track(self, track: str) -> Optional[PreviousAnalysisResult]:
        return await asyncio.to_thread(
            self._scan_average_sync,
            "#track = :track",
            {":track": {"S": track}},
        )

    async def list_company_track_stats(
        self, track: str, minimum_sample_count: int
    ) -> List[HistoricalCompanyStats]:
        return await asyncio.to_thread(
            self._scan_company_track_stats_sync,
            track,
            minimum_sample_count,
        )

    async def get_resume_text(self, id_: str) -> Optional[str]:
        return await asyncio.to_thread(self._get_resume_text_sync, id_)

    # --- sync internals (run in worker thread) ---

    def _get_resume_text_sync(self, id_: str) -> Optional[str]:
        try:
            response = self._client.get_item(
                TableName=self._tables.document_context,
                Key={"id": {"S": id_}},
            )
            item = response.get("Item")
            if item and "context" in item:
                return item["context"].get("S")
            return None
        except Exception as exc:  # noqa: BLE001 - mirrors Java's DynamoDbException catch
            logger.debug("getResumeText failed: %s", exc)
            return None

    def _scan_average_sync(
        self, filter_expression: str, expression_values: Dict[str, Any]
    ) -> Optional[PreviousAnalysisResult]:
        rows: List[PreviousAnalysisResult] = []
        exclusive_start_key: Optional[Dict[str, Any]] = None

        try:
            while True:
                expression_names = {"#track": "track"}
                if "#company" in filter_expression:
                    expression_names["#company"] = "company"
                kwargs: Dict[str, Any] = {
                    "TableName": self._tables.resume_coordinates,
                    "FilterExpression": filter_expression,
                    "ExpressionAttributeNames": expression_names,
                    "ExpressionAttributeValues": expression_values,
                }
                if exclusive_start_key:
                    kwargs["ExclusiveStartKey"] = exclusive_start_key

                response = self._client.scan(**kwargs)
                for item in response.get("Items", []):
                    parsed = self._to_previous_analysis_result(item)
                    if parsed is not None:
                        rows.append(parsed)

                exclusive_start_key = response.get("LastEvaluatedKey")
                if not exclusive_start_key:
                    break
        except Exception as exc:  # noqa: BLE001
            logger.debug("scanAverage failed: %s", exc)
            return None

        return self._average(rows)

    def _scan_company_track_stats_sync(
        self, track: str, minimum_sample_count: int
    ) -> List[HistoricalCompanyStats]:
        grouped: Dict[str, List[PreviousAnalysisResult]] = defaultdict(list)
        exclusive_start_key: Optional[Dict[str, Any]] = None

        try:
            while True:
                kwargs: Dict[str, Any] = {
                    "TableName": self._tables.resume_coordinates,
                    "FilterExpression": "#track = :track",
                    "ExpressionAttributeNames": {"#track": "track"},
                    "ExpressionAttributeValues": {":track": {"S": track}},
                }
                if exclusive_start_key:
                    kwargs["ExclusiveStartKey"] = exclusive_start_key

                response = self._client.scan(**kwargs)
                for item in response.get("Items", []):
                    parsed = self._to_previous_analysis_result(item)
                    company = (parsed.company or "").strip() if parsed is not None else ""
                    if company:
                        grouped[company].append(parsed)

                exclusive_start_key = response.get("LastEvaluatedKey")
                if not exclusive_start_key:
                    break
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "company track statistics scan failed: track=%s failureCategory=%s",
                track,
                type(exc).__name__,
            )
            return []

        results: List[HistoricalCompanyStats] = []
        for company, rows in grouped.items():
            if len(rows) < minimum_sample_count:
                continue
            average = self._average(rows)
            if average is None:
                continue
            results.append(
                HistoricalCompanyStats(
                    company=company,
                    track=track,
                    sample_count=len(rows),
                    x=average.x,
                    y=average.y,
                    z=average.z,
                    overall=self._average_score(average.x, average.y, average.z),
                )
            )

        return sorted(
            results,
            key=lambda item: (item.sample_count, item.overall, item.company),
            reverse=True,
        )

    def _to_previous_analysis_result(self, item: Dict[str, Any]) -> Optional[PreviousAnalysisResult]:
        try:
            company = item.get("company", {}).get("S")
            position = item.get("position", {}).get("S")
            track = item.get("track", {}).get("S")
            x = float(item["x"]["N"])
            y = float(item["y"]["N"])
            z = float(item["z"]["N"])
            overall = float(item["overall"]["N"]) if "overall" in item else self._average_score(x, y, z)
            return PreviousAnalysisResult(
                company=company, position=position, track=track, x=x, y=y, z=z, overall=overall
            )
        except (KeyError, TypeError, ValueError):
            return None

    def _average(self, rows: List[PreviousAnalysisResult]) -> Optional[PreviousAnalysisResult]:
        if not rows:
            return None

        first = rows[0]
        x = sum(r.x for r in rows) / len(rows)
        y = sum(r.y for r in rows) / len(rows)
        z = sum(r.z for r in rows) / len(rows)
        overall = sum(r.overall for r in rows) / len(rows)

        return PreviousAnalysisResult(
            company=first.company,
            position=first.position,
            track=first.track,
            x=self._round(x),
            y=self._round(y),
            z=self._round(z),
            overall=self._round(overall),
        )

    def _average_score(self, x: float, y: float, z: float) -> float:
        return self._round((x + y + z) / 3.0)

    @staticmethod
    def _round(value: float) -> float:
        return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
