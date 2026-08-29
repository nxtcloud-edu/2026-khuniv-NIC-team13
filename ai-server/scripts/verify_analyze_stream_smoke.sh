#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
URL="${PERTINEO_SMOKE_URL:-http://localhost:8080/api/agent/analyze/stream}"
STARTUP_TIMEOUT_SECONDS="${PERTINEO_STARTUP_TIMEOUT_SECONDS:-120}"
STREAM_TIMEOUT_SECONDS="${PERTINEO_STREAM_TIMEOUT_SECONDS:-20}"
KEEP_RESPONSE="${PERTINEO_KEEP_SMOKE_RESPONSE:-0}"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "docker compose or docker-compose is required" >&2
  exit 127
fi

payload_file="$(mktemp)"
response_file="$(mktemp)"
cleanup() {
  rm -f "$payload_file"
  if [[ "$KEEP_RESPONSE" != "1" ]]; then
    rm -f "$response_file"
  else
    echo "Smoke response kept at: $response_file"
  fi
}
trap cleanup EXIT

cat > "$payload_file" <<'JSON'
{
  "userId": "dbsghwns1209@khu.ac.kr",
  "questionList": [
    "당사에 지원하게 된 동기와 입사 후 포부에 대해 서술해 주십시오.",
    "지원한 직무를 수행하기 위해 본인이 갖춘 역량과 관련된 경험을 구체적으로 서술해 주십시오."
  ],
  "answerList": [
    "전국 규모의 유통망을 연결하는 안정적인 IT 시스템 운영과 혁신적인 인프라 구축 비전에 공감하여 지원했습니다. 입사 후에는 시스템 모니터링 자동화와 클라우드 인프라 최적화를 통해 운영 효율성을 높이는 IT 관리자가 되겠습니다.",
    "컴퓨터공학을 전공하며 React와 Spring Boot를 활용한 실시간 웹 모니터링 서비스를 구축하고 GCP 환경에 성공적으로 배포한 경험이 있습니다. 또한 LangGraph와 FastAPI를 이용해 데이터를 분석하는 AI 에이전트를 개발하며 최신 IT 트렌드와 인프라 운영 역량을 길렀습니다."
  ],
  "education": "대학교(4년제) 졸업",
  "gpa": 3.8,
  "major": "컴퓨터공학",
  "backgroundCareerAward": "모니터링 시스템 구축 프로젝트, AI 에이전트 개발 경험",
  "linguisticAbility": "TOEIC 850",
  "certificates": "정보처리기사, Oracle Database SQL Certified Associate",
  "company": "삼성",
  "jobPosition": "IT",
  "jobField": "IT/개발",
  "division": "IT본부",
  "applyUrl": "https://recruit.company.com/apply/10293"
}
JSON

cd "$ROOT"

echo "=== Build and start compose stack ==="
"${COMPOSE[@]}" up -d --build

echo "=== Wait for app to answer on localhost:8080 ==="
deadline=$((SECONDS + STARTUP_TIMEOUT_SECONDS))
while (( SECONDS < deadline )); do
  code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 3 http://localhost:8080/ || true)"
  if [[ "$code" != "000" ]]; then
    echo "App is reachable with HTTP $code"
    break
  fi
  sleep 2
done

if [[ "${code:-000}" == "000" ]]; then
  echo "App did not become reachable within ${STARTUP_TIMEOUT_SECONDS}s" >&2
  "${COMPOSE[@]}" ps >&2 || true
  exit 1
fi

echo "=== POST smoke request to $URL ==="
set +e
http_code="$(curl -sS -N \
  --connect-timeout 5 \
  --max-time "$STREAM_TIMEOUT_SECONDS" \
  -o "$response_file" \
  -w '%{http_code}' \
  -H 'Content-Type: application/json' \
  -X POST \
  --data-binary "@$payload_file" \
  "$URL")"
curl_exit=$?
set -e

# SSE streams can stay open longer than the smoke timeout. Treat curl timeout as OK
# only when the server already accepted the request with HTTP 200.
if [[ "$http_code" == "200" ]]; then
  echo "PASS: $URL returned HTTP 200 (curl exit: $curl_exit)."
  exit 0
fi

echo "FAIL: expected HTTP 200, got '${http_code:-none}' (curl exit: $curl_exit)." >&2
if [[ -s "$response_file" ]]; then
  echo "--- response excerpt ---" >&2
  head -c 2000 "$response_file" >&2 || true
  echo >&2
fi
"${COMPOSE[@]}" ps >&2 || true
exit 1
