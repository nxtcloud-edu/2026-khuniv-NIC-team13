"""Port of ``pertineo.agent.service.SmartParsingMetricsLogger``."""
from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from app.service.smart_parsing_models import SmartParsingMetric

logger = logging.getLogger(__name__)

_MILLION = Decimal(1_000_000)
_NANO_INPUT_RATE = Decimal("0.05")
_NANO_OUTPUT_RATE = Decimal("0.40")
_MINI_INPUT_RATE = Decimal("0.25")
_MINI_OUTPUT_RATE = Decimal("2.00")


class SmartParsingMetricsLogger:
    def log_metric(self, metric: SmartParsingMetric) -> None:
        try:
            logger.info("smart_parsing_metric=%s", metric.model_dump_json())
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to serialize smart parsing metric: %s", exc)

    def estimate_cost_usd(
        self, model: Optional[str], input_tokens: Optional[int], output_tokens: Optional[int]
    ) -> Optional[str]:
        if model is None or input_tokens is None or output_tokens is None:
            return None

        if model == "gpt-5-nano":
            input_rate, output_rate = _NANO_INPUT_RATE, _NANO_OUTPUT_RATE
        elif model == "gpt-5-mini":
            input_rate, output_rate = _MINI_INPUT_RATE, _MINI_OUTPUT_RATE
        else:
            return None

        input_cost = (Decimal(input_tokens) / _MILLION) * input_rate
        output_cost = (Decimal(output_tokens) / _MILLION) * output_rate
        total = (input_cost + output_cost).quantize(Decimal("1.000000000000"), rounding=ROUND_HALF_UP)
        return str(total)
