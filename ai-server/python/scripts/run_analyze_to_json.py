#!/usr/bin/env python3
"""Run /api/agent/analyze/stream against a running server and save the final
combined result as a single JSON file, ready for json_to_pdf_report.py.

Usage:
    python scripts/run_analyze_to_json.py
    python scripts/run_analyze_to_json.py --host http://127.0.0.1:8080 \
        --request scripts/sample_analyze_request.json \
        --out scripts/analysis_result.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

# SSE event types worth keeping in the saved JSON. Everything else (the
# intermediate "_start"/"_generation" progress events) is just logged to
# stdout as it streams by.
SIGNIFICANT_TYPES = {
    "schemer_result",
    "schemer_result_track",
    "pass_score",
    "pass_score_none",
    "web_search_plan_generated",
    "evaluate_vector_context",
    "evaluate_result",
    "revise_result",
    "workflow_error",
}


def _elapsed_between(
    events: List[Dict[str, Any]], start_type: str, end_type: str
) -> Optional[float]:
    started = next(
        (event["elapsed_seconds"] for event in events if event["type"] == start_type),
        None,
    )
    ended = next(
        (event["elapsed_seconds"] for event in events if event["type"] == end_type),
        None,
    )
    if started is None or ended is None:
        return None
    return round(ended - started, 3)


def run(host: str, request_path: Path, out_path: Path, timeout: float) -> int:
    request_body: Dict[str, Any] = json.loads(request_path.read_text(encoding="utf-8"))

    collected: Dict[str, Any] = {}
    events_log: List[Dict[str, Any]] = []
    failed = False

    url = f"{host.rstrip('/')}/api/agent/analyze/stream"
    print(f"POST {url}")
    print(f"  company={request_body.get('company') or request_body.get('applying_to')}  "
          f"jobPosition={request_body.get('jobPosition') or request_body.get('applying_as')}")
    print()

    started = time.perf_counter()
    with httpx.Client(timeout=timeout) as client:
        with client.stream("POST", url, json=request_body) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload = json.loads(line[len("data:"):].strip())
                event_type = payload.get("type")
                status = payload.get("status")
                data = payload.get("data")

                events_log.append({
                    "type": event_type,
                    "status": status,
                    "elapsed_seconds": round(time.perf_counter() - started, 3),
                })
                print(f"  [{status}] {event_type}")

                if status == "FAILED":
                    failed = True
                if event_type in SIGNIFICANT_TYPES:
                    collected[event_type] = data

    elapsed_seconds = round(time.perf_counter() - started, 3)
    node_seconds = {
        "SCHEMER": _elapsed_between(events_log, "schemer_start", "schemer_end"),
        "WEBSEARCH": _elapsed_between(events_log, "web_search_start", "web_search_end"),
        "DATA": _elapsed_between(events_log, "web_search_end", "evaluate_start"),
        "EVALUATE": _elapsed_between(events_log, "evaluate_start", "evaluate_end"),
        "REVISE": _elapsed_between(events_log, "revise_start", "revise_result"),
    }
    fallback_types = {
        "schemer_recheck",
        "workflow_retrying",
        "evaluate_strategy_fallback",
        "revise_targeted_repair",
        "revise_numeric_qualifier_restore",
        "revise_explanation_fallback",
        "revise_safe_fallback",
        "pass_score_none",
    }
    fallbacks = [
        event["type"] for event in events_log if event["type"] in fallback_types
    ]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "request": request_body,
        "failed": failed,
        "elapsed_seconds": elapsed_seconds,
        "node_seconds": node_seconds,
        "fallbacks": fallbacks,
        "schemer_result": collected.get("schemer_result"),
        "track": collected.get("schemer_result_track"),
        "pass_score": collected.get("pass_score") or collected.get("pass_score_none"),
        "vector_context": collected.get("evaluate_vector_context"),
        "evaluate_result": collected.get("evaluate_result"),
        "revise_result": collected.get("revise_result"),
        "event_log": events_log,
        "report_notes": [
            "이 문서는 sample_analyze_request.json으로 실제 전체 워크플로를 1회 실행한 결과입니다.",
            "실행 범위에는 Schemer, 웹 검색, 데이터 조회, 벡터 컨텍스트 조회, Evaluate, Reviser가 모두 포함됩니다.",
            f"전체 응답 시간은 {elapsed_seconds:.3f}초입니다.",
            "노드 시간: "
            + ", ".join(
                f"{node}={seconds:.3f}초"
                for node, seconds in node_seconds.items()
                if seconds is not None
            ),
            "관찰된 fallback: " + (", ".join(fallbacks) if fallbacks else "없음"),
        ],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(f"Saved: {out_path}")

    if failed:
        print("NOTE: the workflow reported a failure at some point — check event_log below.")
    if collected.get("evaluate_result") is None:
        print("WARNING: no evaluate_result captured — the PDF report will be incomplete.")
    return 1 if failed else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="http://127.0.0.1:8080", help="Running server base URL")
    parser.add_argument(
        "--request", default="scripts/sample_analyze_request.json", type=Path,
        help="Path to the analyze request JSON body",
    )
    parser.add_argument(
        "--out", default="scripts/analysis_result.json", type=Path,
        help="Where to write the combined result JSON",
    )
    parser.add_argument("--timeout", type=float, default=600.0, help="Request timeout in seconds")
    args = parser.parse_args(argv)

    return run(args.host, args.request, args.out, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
