# Pertineo AI — Python port

FastAPI port of the Java/Spring Boot service in `src/`. Same resume-analysis
workflow, same API contract, same prompt/resource files (copied verbatim
into `resources/`). This directory is additive — the original Java service
under `src/` is untouched.

## Layout

```
python/
  app/
    config/        settings (env-driven, mirrors application*.yml)
    controllers/    FastAPI routers (/api/agent, /api/parse)
    schemas/        request DTOs
    mappers/        DTO -> AgentState
    repository/     DynamoDB access
    vector/         OpenAI embeddings + S3 Vectors search
    cache/          in-process TTL cache for web search results
    trace/          LangSmith tracer
    service/        smart parsing (rule-based + LLM fallback)
    workflow/       state graph engine + nodes (schemer, websearch, data, evaluate, revise)
  resources/        prompts, dummy data, track definitions (copied from src/main/resources)
  tests/            pytest suite mirroring the Java test suite
```

## Setup

```bash
cd python
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
```

Copy the safe template and put credentials only in the ignored local file:

```bash
cp .env.example .env
chmod 600 .env
```

Active runtime environment variables:

- `SPRING_PROFILES_ACTIVE` — `local` (default) or `prod`
- `LOG_LEVEL`, `VERBOSE_LIBS` — application and optional library log verbosity
- `OPENAI_API_KEY` — structured output, resume parsing, and embeddings
- `OPENAI_CHAT_MODEL` — workflow/career structured-output model; defaults to `gpt-5.6-luna`
- `OPENAI_REASONING_EFFORT` — `none`, `low`, `medium`, `high`, `xhigh`, or `max`
- `TAVILY_API_KEY`
- `AWS_REGION`, `DYNAMODB_ENDPOINT` (local), `AWS_DYNAMODB_ENDPOINT` (prod)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` — optional static/temporary AWS credentials
- `AWS_DYNAMODB_TABLE_RESUME_COORDINATES`, `AWS_DYNAMODB_TABLE_DOCUMENT_CONTEXT`
- `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`
- `SMART_PARSING_PRIMARY_MODEL`, `SMART_PARSING_FALLBACK_MODEL`, `SMART_PARSING_FALLBACK_ENABLED`, `SMART_PARSING_FALLBACK_MAX_CHARS`
- `RESUME_FILE_PARSING_MODEL` — PDF/DOCX/TXT structured extraction model

A `.env` file in `python/` is picked up automatically. The active server no
longer reads Friendli, EXAONE, Upstage, or `EMBEDDING_PROVIDER` settings.

## Legacy embedding evaluation tools

The historical Upstage comparison/re-embedding scripts remain under `tools/`
for reproducibility, but they are not imported by the active application and
their credentials are intentionally omitted from `.env.example`.

Upstage Embed 2 used separate models in one shared vector space:

- `solar-embedding-2-passage` embeds the stored resume documents.
- `solar-embedding-2-query` embeds incoming search requests.
- Both return 1,024-dimensional vectors. They cannot be mixed with the current
  OpenAI 1,536-dimensional index.

Any historical rerun must use an isolated, uncommitted environment and the
parallel 1,024-dimensional index. The active runtime always uses the existing
OpenAI 1,536-dimensional index.

```bash
cd python

# Validate all 1,991 exported records without calling Upstage or AWS.
../.venv/bin/python tools/reembed_upstage.py --dry-run

# Validate the already generated local vectors without accessing AWS.
../.venv/bin/python tools/upload_local_vectors.py --dry-run

# Upload only upstage_vectors.jsonl. This does not call Upstage/OpenAI and does
# not read or upload document_context/resume_coordinates. Add
# --create-resources only when the new bucket/index does not exist yet.
../.venv/bin/python tools/upload_local_vectors.py \
  --profile pertineo-personal \
  --create-resources
```

The upload command writes `upstage_vectors.upload_report.json` beside the
private export. It must not replace the active OpenAI index configured by
`S3_VECTORS_INDEX`.

## Run

```bash
uvicorn app.main:app --reload --port 8080
```

Or via Docker (includes DynamoDB Local):

```bash
docker compose up --build
```

## Test

```bash
pytest
```

## API

Identical routes/contract to the Java service:

- `POST /api/agent/analyze/stream` — SSE stream of workflow events (`text/event-stream`)
- `POST /api/parse/convert` — smart-parses a raw resume text blob into question/answer lists
- `POST /api/career/recommendations` — infers suitable roles when omitted, verifies current job links, and returns up to three auditable recommendations
- `POST /api/career/company-recommendations` — derives role evidence and X/Y/Z scores from a self-introduction, ranks companies with sufficient historical successful-application samples, verifies current job links, and returns up to three evidence-backed companies
- `POST /api/career/roadmap` — aggregates repeated requirements and profile gaps from verified jobs, then returns exact 1/3/6/12-month milestones

The company recommendation endpoint intentionally reports a historical-fit
score, not an acceptance probability. The current dataset contains successful
application score baselines but no explicit failed-application population.
The default request requires at least ten historical records per company and
track before that company can be considered.

```bash
curl -sS -X POST http://127.0.0.1:8080/api/career/company-recommendations \
  -H 'Content-Type: application/json' \
  --data-binary @scripts/sample_company_recommendation_request.json
```

## Scripts (standalone, not part of the API)

`scripts/` has two independent CLI scripts for pulling an analysis result out
to a file and turning it into a PDF report. These are separate from the API
on purpose — login/PDF delivery is handled by another service; this one is
just the AI server.

```bash
pip install -r scripts/requirements-scripts.txt

# 1) run the workflow against a running server, save the result as JSON
python scripts/run_analyze_to_json.py --host http://127.0.0.1:8080 \
  --request scripts/sample_analyze_request.json --out scripts/analysis_result.json

# 2) turn that JSON into a formatted PDF report (Korean-capable, bundled font)
python scripts/json_to_pdf_report.py --json scripts/analysis_result.json \
  --out scripts/analysis_report.pdf
```
