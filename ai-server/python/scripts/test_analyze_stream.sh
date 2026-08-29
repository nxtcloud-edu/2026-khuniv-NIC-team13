#!/usr/bin/env bash
# Streams the /api/agent/analyze/stream SSE response to your terminal.
# Run from the python/ directory while the server is up:
#   ./scripts/test_analyze_stream.sh
set -euo pipefail

HOST="${HOST:-http://127.0.0.1:8080}"

curl -N -sS -X POST "$HOST/api/agent/analyze/stream" \
  -H "Content-Type: application/json" \
  -d @scripts/sample_analyze_request.json
