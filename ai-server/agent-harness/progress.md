# Agent Progress Log

## 2026-08-29 — Data-backed company recommendations v1

Goal: recommend up to three currently actionable companies using explicit role
evidence, historical successful-application score baselines, sample confidence,
and verified live job requirements.

Workflow:
- The user's earlier issue-first waiver was continued for this related career
  feature.
- Branch: `feature/data-backed-company-recommendations`, based on
  `refactor/openai-provider-unification`.
- Implementation commit: `80321a2` (`Lore: rank companies with historical
  success evidence`).
- Issue/PR: not created; no publication was requested in this pass.

Changed:
- Added `POST /api/career/company-recommendations` for structured profile plus
  self-introduction question/answer input.
- Added an OpenAI structured assessment that returns `business`/`engineering`,
  one to three roles with input-grounded evidence, and rubric-based X/Y/Z
  scores; `userId` and raw `resumeText` are excluded from that model request.
- Added a paginated DynamoDB aggregation that groups company/track historical
  scores and enforces a configurable sample floor (default 10).
- Candidate companies now originate from historical alignment before Tavily
  search. Current active jobs are then verified and scored, and the final
  deterministic score is historical alignment 50 + active job fit 40 + sample
  confidence 10.
- Responses expose historical sample counts, averages, applicant gaps,
  confidence, active job links, evidence, gaps, and an explicit disclaimer that
  the result is not an acceptance probability.
- Added a synthetic, reproducible request at
  `python/scripts/sample_company_recommendation_request.json`.

Verification:
- Baseline focused career/repository suite: 16 passed.
- Initial TDD collection failed on the intentionally missing company models.
- Focused company/career/repository/app suite: 31 passed.
- Full Python suite: 162 passed with one existing Starlette/httpx warning.
- Python compile and `git diff --check` passed.
- Live read-only DynamoDB preflight: engineering track, minimum sample 10 ->
  38 eligible companies and 1,866 historical samples.
- Loaded `python/.env` through Uvicorn's dotenv support and restarted the
  current branch on `127.0.0.1:8080`; OpenAPI exposed the new route.
- One synthetic end-to-end request completed with HTTP 200 in 43.110 seconds.
  OpenAI Responses calls used `gpt-5.6-luna`, Tavily searches returned HTTP
  200, and DynamoDB aggregates supplied ten candidate companies. Four
  companies had a page classified as active and three results were returned.
- The response inferred engineering and backend/data-platform/cloud-backend
  roles, then returned KT (78, n=66), SK Telecom (78, n=60), and LG Electronics
  (77, n=347). All three overall scores exactly matched their 50/40/10
  breakdowns, company names were distinct, and result URLs were external HTTP
  links. The saved response is
  `/private/tmp/pertineo-company-recommendation-live.json` with SHA-256
  `dab9f3d057cd6f3ae11e40e7a4ea1538590aedb8ada35652ed5659483e08b9b5`.

Live quality gaps:
- The successful run is transport/schema proof, not quality approval. All
  selected job records had zero role-match contribution and no extracted
  required/preferred requirements.
- The LG Electronics recommendation linked to an LG Electronics partner-company
  listing, so the historical company and active-job company names did not
  match. Generic company recruiting pages were accepted for KT and SK Telecom.
- The next isolated improvement should require an exact normalized company
  match, reject generic listing pages without a concrete role/title, and
  require positive role evidence plus extracted requirements before a posting
  can qualify as `verified_active`.

## 2026-08-29 — OpenAI provider unification

Goal: replace the active Friendli/EXAONE and Upstage model paths with direct
OpenAI APIs while preserving public routes, structured response schemas, and
the existing OpenAI S3 Vector index.

Workflow:
- The user explicitly waived issue creation and requested `origin/khu_nexus`
  as the reference implementation.
- Branch: `refactor/openai-provider-unification`, based on
  `feature/career-roadmap` commit `777b694`.
- Commit: `e6bd9ba`, pushed to
  `origin/refactor/openai-provider-unification`.
- Issue/PR: not created; the GitHub connector cannot access this private
  repository and the user waived the issue-first step.

Changed:
- Replaced Friendli Chat Completions structured calls with OpenAI Responses
  API `responses.parse`, including `instructions`, `input`, Pydantic
  `text_format`, explicit reasoning effort, output limits, and `store=false`.
- Added `OPENAI_CHAT_MODEL` (`gpt-5.6-luna`) and
  `OPENAI_REASONING_EFFORT`; removed Friendli/EXAONE/Upstage provider fields
  from active runtime Settings and `.env.example`.
- Kept Smart Parsing's OpenAI `gpt-5-nano` to `gpt-5-mini` fallback instead of
  collapsing the existing tiered route.
- Fixed active query embeddings to OpenAI `text-embedding-3-small` and the
  existing 1,536-dimensional S3 Vector index.
- Preserved historical EXAONE/Upstage comparison and migration tools outside
  active runtime settings; the legacy comparison script now reads its own
  optional provider variables.
- Updated workflow, career, environment, documentation, and mocked SDK
  contract tests.

Verification:
- Baseline focused provider suite: 17 passed.
- Post-change focused workflow/provider/career suite: 83 passed.
- Full Python suite: 157 passed with one existing Starlette/httpx deprecation
  warning.
- A real OpenAI Python SDK client with `httpx.MockTransport` serialized the
  Responses JSON-schema request and parsed it back into the Pydantic result.
- Restarted Uvicorn from the integration branch with a process-local
  placeholder OpenAI key; `GET /openapi.json` returned HTTP 200 and exposed
  the analysis, parse, recommendation, and roadmap routes.
- Python compile checks, feature JSON validation, script `--help` checks, and
  `git diff --check` passed.
- The documented `./gradlew build` could not run because this Python checkout
  has no Gradle wrapper; `init.sh` is stale for the current repository shape.

Risks / gaps:
- No live OpenAI, Tavily, DynamoDB, or S3 request was made; external behavior
  remains mock/fake backed and no API cost was incurred.
- Existing ignored `.env` files may still contain obsolete Friendli/Upstage
  values; the active Settings class ignores them, but they should be removed
  during local secret cleanup.
- Historical provider comparison scripts remain for reproducibility and are
  not part of the active server dependency path.

## 2026-08-29 — Career feature delivery

Delivery:
- A commit: `8910238` (`feature/career-job-recommendations`), pushed to `origin/feature/career-job-recommendations`.
- B commit: `e1247c5` (`feature/career-roadmap`), pushed to `origin/feature/career-roadmap`.
- PRs were not opened because no authenticated GitHub issue/PR tool was available; the user explicitly waived issue-first workflow for both features.

Final verification:
- Full Python suite: 152 passed, one existing Starlette/httpx deprecation warning.
- Focused career/controller/app suite: 15 passed.
- Career/controller/schema compile check passed.
- Feature JSON validation and `git diff --check` passed.
- Restarted Uvicorn from `feature/career-roadmap`; `/openapi.json` returned the two final routes: `/api/career/recommendations` and `/api/career/roadmap`.
- Server remains running on `http://127.0.0.1:8080` with a process-local placeholder OpenAI key; real resume OCR is unavailable until a valid key is configured.

Live-integration gap:
- No Tavily/Friendli request was made, so no external private data was transmitted and no API cost was incurred.

## 2026-08-29 — Target career roadmap

Goal: implement feature B, deriving target-role/company requirements, profile gaps, and exact 1/3/6/12-month milestones from verified job recommendations.

Workflow:
- The user's issue-first waiver covers both planned career features.
- Branch: `feature/career-roadmap`, based on A commit `8910238`.
- Issue/PR: not created because authenticated GitHub issue/PR tooling remains unavailable.

Changed:
- Added `POST /api/career/roadmap` with target role required and target company optional.
- Reused the verified recommendation pipeline instead of creating a second search path.
- Aggregated only requirements repeated across at least two distinct reference job URLs and returned category, source count, and source URLs.
- Derived priority gaps in code only when the local profile has no matching evidence.
- Added a privacy-minimized roadmap prompt that excludes `userId` and raw resume text.
- Added strict ordered 1/3/6/12-month validation and a deterministic four-horizon fallback for model/provider failure.

Verification:
- Initial TDD collection failed as expected because roadmap schemas/models did not exist.
- Focused recommendation/roadmap/controller/app tests: 15 passed, one existing warning.
- Full after edits: `cd python && ../.venv/bin/python -m pytest -q` -> 152 passed, one existing Starlette/httpx deprecation warning.
- `python -m compileall` for career/controller/schema paths passed.
- `git diff --check` passed.
- Ruff remains unavailable in the local virtual environment.

Risks / gaps:
- No live Tavily/Friendli call was made; all external behavior is fake/mock backed.
- Requirement aggregation currently normalizes case and whitespace but does not semantically merge differently worded equivalent requirements.
- The roadmap is limited by the number and quality of active job pages that pass server-side verification.

## 2026-08-29 — Career job recommendations

Goal: implement feature A, returning up to three verified job-posting links ranked from the applicant's structured career profile.

Workflow:
- User explicitly waived the issue-first requirement after the configured GitHub connector could not access the repository, `gh` was unavailable, and no signed-in browser session was present.
- Branch: `feature/career-job-recommendations`, based on current `main`.
- Issue/PR: not created because no authenticated GitHub issue/PR surface was available.

Changed:
- Added a separate `career` domain with profile-based role inference, Friendli/EXAONE structured planning and extraction, Tavily job search, bounded URL verification, canonical deduplication, grounded deadlines, and deterministic ranking.
- Added `POST /api/career/recommendations`; target roles are optional and resolved roles plus a transparent score breakdown are returned.
- Excluded `userId` and raw resume text from discovery-planning prompts; raw resume text is used only for local requirement matching.
- Added app/container lifecycle wiring and career-specific prompt resources.
- Completed `python/.env.example` with all runtime setting aliases plus log controls and documented the recommendation route.

Verification:
- Baseline before edits: `cd python && ../.venv/bin/python -m pytest -q` -> 137 passed, one existing Starlette/httpx deprecation warning.
- Initial TDD collection failed as expected because career modules did not exist.
- Focused contract/app tests: 10 passed, then 11 passed after environment example coverage.
- Full after edits: `cd python && ../.venv/bin/python -m pytest -q` -> 147 passed, one existing warning.
- `python -m compileall` for career/controller/schema paths passed.
- `git diff --check` passed.
- Ruff was not run because the local virtual environment has no `ruff` executable.

Risks / gaps:
- Live Tavily/Friendli calls were not run; tests use fakes and `httpx.MockTransport`.
- JavaScript-rendered or bot-protected recruiting pages may be classified as `unknown` and intentionally excluded.
- DNS-resolving hostnames are screened by URL/hostname policy, but a production network egress policy remains the strongest SSRF boundary.

## 2026-08-28 — Resume file parsing endpoint restoration

Goal: restore the Python AI server endpoint required by the main server's
`POST /api/parse/file` proxy and return form-compatible resume fields.

GitHub:
- Issue: #3 https://github.com/Team-Pertineo/pertineo_ai_server/issues/3
- Branch: `fix/resume-file-parsing-endpoint`

Changed:
- Added a validated PDF/DOCX/TXT multipart endpoint at `/api/parse/file`.
- Added an OpenAI Responses API file-input adapter with structured `ParseResult` output.
- Added an extraction contract limited to education, experience, awards,
  certifications, and language fields consumed by the client.
- Added route, validation, and OpenAI request-shape tests with fakes.

Verification:
- `PYTHONPATH=python .venv/bin/python -m pytest -q python/tests` passed: 137 tests.
- Python compile, feature JSON validation, and `git diff --check` passed.
- Docker image build was attempted but Docker Desktop was not running, so no
  container build result is claimed.

Risks / gaps:
- Live OpenAI file parsing was not invoked locally; tests use a fake Responses client.
- Production AI service deployment and end-to-end upload smoke remain required.

## 2026-05-22 — Harness bootstrap

Goal: create a project-specific AI coding-agent harness for Pertineo AI 2.0.

Created:
- `AGENTS.md`: root routing instructions and verification contract
- `docs/agent-harness.md`: detailed five-subsystem harness guide
- `agent-harness/feature_list.json`: feature/state tracker
- `agent-harness/progress.md`: session continuity log
- `agent-harness/session-handoff.md`: restart packet template/current state
- `init.sh`: standard local verification entrypoint

Observed project shape:
- Java 21 / Spring Boot 4.0.5 / Gradle
- SSE controller at `/api/agent/analyze/stream`
- Workflow nodes under `pertineo.agent.workflow`
- DynamoDB repository test already present

Verification:
- `./init.sh` first failed inside sandbox because Gradle wrapper needed `/root/.gradle` write access.
- `./init.sh` rerun outside sandbox reached `./gradlew --no-daemon test`.
- Result: failed at `:compileTestJava`; `DynamoDbPreviousResumeDataRepositoryTest` calls missing method `getScoreByCompanyAndPosition(String,String)` on `DynamoDbPreviousResumeDataRepository`.

Risks / gaps:
- Repository had many pre-existing modified files before harness creation; harness work must not overwrite unrelated changes.
- External integrations must remain mocked/faked in tests unless live validation is explicitly required.

## 2026-05-22 — Verification note

Harness file creation complete. Baseline build is red for an existing Java test/API mismatch unrelated to harness files. Next coding session should either restore repository method coverage or update/remove stale test expectation before claiming full build health.

## 2026-05-22 — Baseline verification fixed

Goal: fix failing harness verification baseline.

Changed:
- `PreviousResumeDataRepository`: restored `getScoreByCompanyAndPosition(String,String)` contract.
- `DynamoDbPreviousResumeDataRepository`: implemented paginated DynamoDB scan, matching company/position rows, averaging x/y/z/overall.
- `application-local.yml`: added default `LANGSMITH_API_KEY:설정안됨` so Spring context tests do not require a secret.

Verification:
- `./gradlew test --tests pertineo.agent.repository.DynamoDbPreviousResumeDataRepositoryTest` passed.
- `./gradlew test --tests pertineo.agent.AgentApplicationTests` passed.
- `./init.sh` passed: Gradle test suite green and harness files present.

Risks / gaps:
- DynamoDB scan implementation is correctness-first for existing contract; future optimization can add query/index support if table schema supports it.

## 2026-05-22 — Removed unused score lookup

Goal: remove `getScoreByCompanyAndPosition` because main code does not call it.

Changed:
- Removed unused repository interface method and DynamoDB implementation.
- Replaced stale score-aggregation test with `getResumeText` test, matching actual `DataNode` usage.

Verification:
- `grep -R "getScoreByCompanyAndPosition" src/main/java src/test/java` has no code references.
- `./gradlew test --tests pertineo.agent.repository.DynamoDbPreviousResumeDataRepositoryTest` passed.
- `./init.sh` passed.

## 2026-05-31 — Workflow event seam refactor

Goal: deepen workflow orchestration/event modules by keeping SSE lifecycle in `StateGraphEngine` while moving event publication behind a small `WorkflowEventSink` seam.

Changed:
- Added `workflow/event/WorkflowEvent`, `WorkflowEventSink`, and `SseWorkflowEventSink`.
- Updated workflow nodes to emit `WorkflowEvent` through `WorkflowEventSink` instead of depending on `SseEmitter` directly.
- Kept selection A: `WorkflowEventSink` only publishes events; `StateGraphEngine` still owns `SseEmitter.complete()` lifecycle.
- Added `WorkflowEventSinkTest` and extended `SchemerNodeTest` to verify event publication without SSE.

Verification:
- `./gradlew test --tests pertineo.agent.workflow.event.WorkflowEventSinkTest --tests pertineo.agent.workflow.nodes.SchemerNodeTest` passed.
- `./gradlew test` passed.

Risks / gaps:
- Public SSE event names/statuses were intentionally preserved; event contract still needs higher-level SSE slice coverage.
- Workflow routing still uses string node names; `WorkflowStep` enum remains the next deepening candidate.

## 2026-05-31 — Harness GitHub workflow rule update

Goal: require issue-first branch workflow and template-matched PR publishing in the project harness.

Changed:
- `AGENTS.md`: added start-of-work GitHub issue/branch requirement, PR template requirement, and issue/PR branding guard.
- `docs/agent-harness.md`: added dedicated GitHub Workflow lifecycle section covering issue templates, branch switching, PR template use, and progress evidence.
- `agent-harness/session-handoff.md`: added resume steps for issue creation, branch switching, and PR template/branding checks.

Verification:
- Forbidden assistant/tool-name string scan across `AGENTS.md`, `docs/agent-harness.md`, `agent-harness/session-handoff.md`, and `.github` returned no matches.
- Documentation-only change; no Gradle tests run.

Risks / gaps:
- This records the procedure but does not create an issue/branch for already-in-progress local changes.

## 2026-05-31 — Published workflow event seam PR

Goal: publish the completed workflow event seam work using the repository issue/PR template flow.

GitHub:
- Issue: #22 https://github.com/khu-return-19/Pertineo-Ai-2.0/issues/22
- Branch: `refactor/agent-node`
- PR: #23 https://github.com/khu-return-19/Pertineo-Ai-2.0/pull/23

Verification:
- PR body followed `.github/PULL_REQUEST_TEMPLATE.md` sections.
- Forbidden assistant/tool-name string scan passed for local issue and PR body temp files before publishing.
- `./gradlew test` had passed before publishing.

Risks / gaps:
- The working tree still contains unrelated pre-existing local modifications not included in PR #23.

## 2026-06-02 — Docker compose stream smoke hook

Goal: add a reproducible completion check for the live `/api/agent/analyze/stream` SSE endpoint.

GitHub:
- Issue: #24 https://github.com/khu-return-19/Pertineo-Ai-2.0/issues/24
- Branch: `test/compose-stream-smoke`

Changed:
- Added `scripts/verify_analyze_stream_smoke.sh` to run `docker compose up -d --build`, wait for `localhost:8080`, POST the canonical 삼성/IT sample payload, and require HTTP 200.
- Updated `AGENTS.md` and `docs/agent-harness.md` to list the script as an optional completion hook for live local SSE validation.
- Updated `.gitignore` to allow this one smoke script to be versioned while leaving other `scripts/` contents ignored.

Verification:
- Baseline before edits: `./gradlew test` passed on branch `test/compose-stream-smoke`.
- After edits: `bash -n scripts/verify_analyze_stream_smoke.sh` passed; `./gradlew test` passed.

Risks / gaps:
- Full smoke execution was not run in this edit pass; it requires Docker plus `.env.dev`/live integration credentials. Run `scripts/verify_analyze_stream_smoke.sh` at completion when those are available.

## 2026-06-02 — Vector evaluation context implementation

Goal: supplement evaluation with vector-similar previous resume/analysis text while preserving existing DB fallback and SSE/response contracts.

GitHub:
- Issue: #26 https://github.com/khu-return-19/Pertineo-Ai-2.0/issues/26
- Branch: `feature/vector-evaluation-context`
- PR: #27 https://github.com/khu-return-19/Pertineo-Ai-2.0/pull/27 (base `dev`, one task commit)

Changed:
- Added `VectorContextService` to build non-blocking topK=3 vector evaluation context from embedding, S3 Vector keys, and `PreviousResumeDataRepository.getResumeText`.
- Updated `EvaluateNode` to pass supplemental `{vector_context}` without changing `{pass_score}` DB context.
- Replaced vector query stdout failure print with `Slf4j` warning.
- Removed unused `VectorSearchResult` record during final cleanup.
- Added minimal vector context instruction to `prompts/evaluate/system.txt`.
- Added tests for vector context success/empty/failure/missing text/repository failure and prompt parameter wiring.

Verification:
- Baseline before edits: `./gradlew test` passed.
- Targeted after edits: `GRADLE_USER_HOME=.gradle ./gradlew --no-daemon test --tests '*VectorContextServiceTest' --tests '*EvaluateNodePromptParametersTest' --stacktrace` passed.
- Full after edits: `GRADLE_USER_HOME=.gradle ./gradlew --no-daemon test` passed.
- Clean PR worktree targeted: `GRADLE_USER_HOME=.gradle ./gradlew --no-daemon test --tests '*VectorContextServiceTest' --tests '*EvaluateNodePromptParametersTest' --stacktrace` passed on `origin/feature/vector-evaluation-context`.
- Clean PR worktree full: `GRADLE_USER_HOME=.gradle ./gradlew --no-daemon test` passed on `origin/feature/vector-evaluation-context`.
- Post-cleanup targeted: `GRADLE_USER_HOME=.gradle ./gradlew --no-daemon test --tests '*VectorContextServiceTest' --tests '*EvaluateNodePromptParametersTest' --stacktrace` passed.
- Final review gate: independent code review APPROVE, architecture review CLEAR; no blocking or advisory findings in scoped implementation.

Risks / gaps:
- Live OpenAI/S3 Vectors/DynamoDB smoke not run; tests use mocks/fakes and full unit suite only.
- Working tree contains pre-existing unrelated modified files; this task touched only vector/evaluate prompt/test files plus harness progress.

## 2026-08-11 — EXAONE workflow reliability and prompt adaptation

Goal: diagnose false Schemer rejection, structured-output stalls, mid-workflow termination, and Reviser hallucination after moving the Python workflow from a frontier model to K-EXAONE.

Workflow:
- User explicitly waived the repository's issue-first requirement for this task and requested direct reporting instead.
- Branch: `exaone-workflow-reliability`.
- Issue/PR/commit: not created.

Changed:
- Added explicit EXAONE non-reasoning/reasoning generation controls, usage logging, bounded SDK retries, and privacy-safe LLM debug logging.
- Changed Schemer to one deterministic validation plus one reasoning confirmation only after rejection; added a dedicated non-retryable invalid-submission exception.
- Fixed per-node retry budget reset, reduced node retry to one, restored state after failed attempts, and corrected retry/completion events.
- Split Evaluate into axes, fit, improvement summary, and improvement strategy schemas; bounded repeated context and added semantic Pydantic validators.
- Changed Reviser from batch-first to question-isolated generation after live testing showed batch repair cost and cross-question fact leakage; added targeted correction and safe original-preserving fallback.
- Added code validation for unsupported numeric claims, Latin technology tokens, foreign-script corruption, question echo, placeholders, and list alignment.
- Added 15-second SSE comment heartbeats while preserving the existing 10-minute no-workflow-event timeout.
- Simplified WebSearch's deterministic plan prompt and Python-only `tool_type` model.
- Fixed DynamoDB track-only scan expression names.
- Added root `memory.md` with research, design decisions, live token measurements, risks, and resume guidance.

Verification:
- Baseline: `cd python && ../.venv/bin/pytest -q` → 44 passed.
- Final: `cd python && ../.venv/bin/pytest -q` → 72 passed, one Starlette/httpx deprecation warning.
- `git diff --check` passed.
- Live EXAONE tests used only fully synthetic applicant/company data and fake Tavily/vector responses.
- Four-stage Evaluate succeeded with 11,261 tokens versus the former one-shot schema failing at 14,967 tokens; the final source-isolated strategy prompt was then rechecked independently at 456 tokens.
- Final question-isolated Reviser with structural evaluation guidance succeeded in 1,721 tokens without repair, cross-question leakage, unsupported numbers, question echo, or corrupt characters.

Risks / gaps:
- No live Tavily, DynamoDB, S3 Vectors, Docker, or end-to-end SSE smoke was run.
- LangSmith sends full AgentState when enabled and still needs a product-level privacy/redaction decision.
- Semantic hallucination cannot be exhaustively proved absent with local validators; continue production-like synthetic eval coverage.

## 2026-08-11 — EXAONE pipeline 10-run consistency benchmark

Goal: measure elapsed time, failure rate, recovery behavior, and response consistency for ten identical synthetic workflow runs.

Added:
- `python/scripts/benchmark_exaone_pipeline_consistency.py`: repeatable synthetic benchmark using real EXAONE calls with fixed fake Tavily/DynamoDB/vector context.

Result:
- Command: `cd python && ../.venv/bin/python scripts/benchmark_exaone_pipeline_consistency.py --runs 10`.
- Pipeline success 10/10; pipeline failure 0/10; total elapsed 169.434 seconds.
- Per-run mean 16.943 seconds, median 16.175, min 15.049, max 22.322.
- Mean stage times: Schemer 0.782, WebSearch 0.963, Data 0.000, Evaluate 11.319, Reviser 3.879 seconds.
- Clean first-pass runs 2/10; at least one internal recovery in 8/10.
- Strategy fallback 7/10, targeted Reviser repair 8/10, safe original-preserving fallback 1/10.
- Track, search queries, and x/y/z scores were identical in all runs; level was `보통` 9/10 and `높음` 1/10 despite identical scores.
- Final revision validation problems 0/10 and detected cross-question leakage 0/10.

Interpretation / next candidates:
- Derive level deterministically from explicit score thresholds.
- Replace or further simplify the strategy LLM call because the local fallback handled 70% of runs.
- Strip exact question echo deterministically before spending a targeted regeneration call.
- Text similarity is lexical SequenceMatcher consistency, not semantic embedding similarity.

## 2026-08-12 — Canonical sample 20-run live pipeline benchmark

Goal: run the exact `python/scripts/sample_analyze_request.json` through the configured workflow 20 times and record every response time, x/y/z score, node duration, fallback, failure node, and consistency result without synthetic measurements.

Workflow:
- The user explicitly allowed the synthetic sample to be sent to configured external services.
- The user continued to waive issue/PR creation and requested direct reporting only.
- Branch: `exaone-workflow-reliability`.

Added:
- `python/scripts/benchmark_sample_pipeline_20runs.py`: validates the request DTO, times each real node attempt, captures workflow/fallback events, failures, scores, fingerprints, and lexical consistency.
- Root `result.md`: complete 20-row measured result, aggregates, failure detail, consistency analysis, and recommended fixes.

Execution:
- Command: `cd python && ../.venv/bin/python scripts/benchmark_sample_pipeline_20runs.py --request scripts/sample_analyze_request.json --runs 20`.
- Input SHA-256: `9331fa84d688cfa4af30fe913509d5390d7874ee6b9ec862ade913dc09d7eaa7`.
- Used the configured real EXAONE/Friendli, Tavily, OpenAI embedding, DynamoDB, S3 Vectors, and LangSmith paths. One Container was reused; runs 2-20 were WebSearch cache hits.

Result:
- Success 19/20; final failure 1/20 at EVALUATE.
- Total 616.657 seconds; mean 30.833, median 26.158, min 23.042, max 74.838 seconds. Run 1 was 37.993 seconds, reproducing the reported near-40-second latency.
- Node means: Schemer 0.574, WebSearch 0.418, Data 0.001, Evaluate 18.567, Reviser 7.455 seconds with the unreached run counted as zero.
- EVALUATE hit `LengthFinishReasonError` in two runs and three attempts total; run 17 recovered, run 2 failed after the second attempt.
- All 19 scored runs produced x/y/z 4.3/4.1/4.2. Level still differed: `높음` once and `보통` 18 times.
- Fallback counts: pass_score_none 20, workflow_retrying 2, evaluate_strategy_fallback 2, revise_targeted_repair 17, revise_safe_fallback 15.
- S3 Vector logged `NoCredentialsError` in every run and continued through its non-blocking fallback. `pass_score_none` also occurred every run, but the repository currently collapses service failures and genuine no-match into the same `None` result.
- On the final failed run, LangSmith also reported a duplicate trace update 409, indicating a likely double-close/update path.

Verification:
- Benchmark script completed all requested 20 iterations and emitted a final aggregate summary.
- `python -m py_compile scripts/benchmark_sample_pipeline_20runs.py` passed before the live execution.
- Final full verification: `cd python && ../.venv/bin/pytest -q` passed with 72 tests and the existing Starlette/httpx deprecation warning.
- `git diff --check` passed; the root result table contains exactly 20 benchmark rows.

Recommended next changes:
- Bound Evaluate substage output lengths and avoid whole-node retries for deterministic length overflow.
- Derive level deterministically from x/y/z.
- Reduce Reviser regeneration by deterministic sanitization and expose safe-original fallback as a quality state rather than plain success.
- Separate AWS no-match, credentials, timeout, and service errors in events/metrics; verify runtime credential-provider wiring.

## 2026-08-12 — Upstage vectors regenerated to local JSONL only

Goal: recreate the deleted Upstage embeddings and retain them locally without accessing or uploading to AWS.

Workflow:
- The user continued to waive issue/PR creation and requested direct reporting only.
- Branch: `embedding-data-export`.

Changed:
- Added `--local-output` to `python/tools/reembed_upstage.py`. This mode does not construct an AWS session/client and appends S3-compatible vector payloads to a resumable local JSONL file.
- Added validation for existing local keys, duplicates, numeric values, and exact 1,024-dimensional vectors.
- Added focused tests for local payload persistence and invalid-dimension rejection.

Execution:
- Input: 1,991 exported document contexts.
- Output: ignored local file `private_exports/embedding_data_20260812/upstage_vectors.jsonl` plus `upstage_vectors.report.json`.
- Result: 1,991/1,991 successful, zero failures/missing keys, 4,240,142 prompt tokens, 694.794 seconds, `aws_accessed=false`.
- Output: 43,865,267 bytes; SHA-256 `35d312afeecd82347105b3c1b19bdbb7c32384a4929bef77fd28741c0661392f`.

Verification:
- Independent JSONL check: 1,991 lines, 1,991 unique keys, all dimensions exactly 1,024, provider/model values consistent.
- `cd python && ../.venv/bin/pytest -q` passed: 87 tests, one existing Starlette/httpx deprecation warning.
- `git diff --check` passed.
- No AWS resource was created, read, updated, or uploaded during local generation.

## 2026-08-12 — Local OpenAI vs Upstage retrieval comparison

Goal: compare retrieval quality proxies, latency, and regressions between the existing OpenAI vectors and regenerated Upstage vectors on the prior test set.

Workflow:
- The user continued to waive issue/PR creation and requested direct reporting only.
- Branch: `embedding-data-export`.

Changed:
- Added `python/tools/compare_local_embeddings.py` for AWS-free exact cosine comparison of both local corpora using identical query text.
- Added focused tests for query formatting, normalization, dimension validation, and ranking metrics.
- Added ignored private reports `embedding_comparison_report.json` and `embedding_comparison.md`.

Execution:
- Corpus: 1,991 matching documents/vectors per provider; OpenAI `text-embedding-3-small` at 1,536 dimensions and Upstage Solar Embedding 2 at 1,024 dimensions.
- Queries: canonical sample plus the 20 most frequent non-empty company/position pairs; primary analysis excludes one `미입력/미입력` placeholder query.
- Valid 19-query results: company hits 32/57→40/57, position hits 8/57→16/57, both hits 6/57→10/57, company Hit@3 13/19→17/19, both Hit@3 unchanged at 4/19, and both nDCG@3 0.412→0.659.
- Paired company outcomes: Upstage wins 10, ties 6, OpenAI wins 3. Paired both-hit outcomes: Upstage wins 3, ties 16, OpenAI wins 0.
- Top-3 overlap was 13/60 (21.7%), indicating materially different context selection.
- Three 21-query batch calls measured median API latency of 0.920 seconds for OpenAI and 0.156 seconds for Upstage; only three runs, so not an SLA benchmark.
- AWS was not accessed.

Verification:
- `cd python && ../.venv/bin/pytest -q` passed: 91 tests and one existing Starlette/httpx deprecation warning.
- `git diff --check` passed.
- Report assertions confirmed `aws_accessed=false`, 1,991 corpus records, 20 legacy queries, and 19 cleaned queries.

Risks / interpretation:
- Relevance is inferred from normalized company/position substrings, not human labels; only five valid queries had exact pair labels in the corpus.
- The directional gain is promising but not statistically conclusive on this sample. Human-labeled retrieval evaluation and a downstream fixed-context EXAONE A/B remain necessary before a final quality claim.
- Make LangSmith trace completion idempotent.

## 2026-08-12 — Saved Upstage vector upload-only path

Goal: prepare a safe AWS upload path that transmits only the regenerated Upstage vectors without re-embedding or touching DynamoDB/source exports.

Workflow:
- The user continued to waive issue/PR creation and requested direct reporting only.
- Branch: `embedding-data-export`.
- No AWS write was executed.

Changed:
- Added `python/tools/upload_local_vectors.py` with local JSONL validation, named-profile precedence, optional resource creation, exact 1,024-dimension index validation, resumable missing-key uploads, and final key verification.
- Added focused loader/upload tests.
- Updated Python migration documentation to use the saved-vector uploader instead of the token-consuming re-embedding path.
- Corrected the `.env.example` target-index typo, added optional AWS session/profile fields, and ignored `.DS_Store`.

Verification:
- Upload dry-run: 1,991 vectors, dimension 1,024, expected SHA-256, `aws_accessed=false`, `embedding_api_accessed=false`, `dynamodb_accessed=false`.
- `cd python && ../.venv/bin/pytest -q` passed: 94 tests and one existing Starlette/httpx deprecation warning.
- `git diff --check` passed.
- Secret-pattern scan over non-ignored repository files returned no findings.
- `upstage_vectors.jsonl`, private reports, `.env`, and `.env.dev` remain Git-ignored.

Remaining:
- AWS CLI profile is not configured yet and no live bucket/index/upload verification has run.
- All changes remain uncommitted; a plain `git push` currently publishes none of this work.

## 2026-08-12 — Production embedding data export

Goal: retrieve every record used by the configured embedding/vector context flow for local inspection and future re-embedding.

Workflow:
- The user explicitly requested the live AWS data export and continued to waive issue/PR creation.
- AWS operations were read-only: DynamoDB `DescribeTable`/`Scan` and S3 Vectors `GetIndex`/`ListVectors`.
- Exported data was placed under Git-ignored `private_exports/` because resume context may contain personal data.

Added:
- `python/tools/export_embedding_data.py`: paginated gzip JSONL export of both DynamoDB tables and the complete S3 Vectors index, with a manifest and per-file SHA-256 hashes.
- `.gitignore`: excludes `private_exports/`.

Result:
- `pertineo-document-context`: 1,991 records.
- `pertino-resume-coordinates`: 5,046 records.
- `pertineo-data-vector-index`: 1,991 vectors; float32 dimension 1,536; cosine distance.
- Document IDs and vector keys matched 1,991/1,991 with no duplicates or missing counterparts. Every vector had dimension 1,536 and metadata ID equal to its key.
- Export directory: `private_exports/embedding_data_20260812/` (20 MB on disk).
- Convenience archive: `private_exports/embedding_data_20260812.tar.gz` (18 MB), SHA-256 `57c0755025e3d029eb3d792fb7f1bfbe182c1ee6a6eecd562777dbd6e1691455`.

Verification:
- All three gzip streams passed `gzip -t`.
- Every JSONL row parsed successfully; counts matched the export manifest.
- `python/tools/export_embedding_data.py --help` passed, and the live full export completed without mutation calls.

Risk:
- This is a consistent read per DynamoDB scan, not an atomic snapshot across DynamoDB and S3 Vectors. Concurrent writes during export could theoretically cause cross-service drift; no drift was observed in the exported key sets.

## 2026-08-13 — EXAONE evaluation output reliability, staged change 1

Goal: preserve approximately the information volume in `python/scripts/analysis_result.json` while making EXAONE prompts less ambiguous, with one change evaluated at a time.

Workflow:
- The user continued to waive issue creation and requested direct change reports and approval between stages.
- Branch: `reviser-output-reliability`, tracking `origin/reviser-output-reliability`.
- No commit or PR was created in this stage.

Changed:
- Clarified one line in `python/resources/prompts/evaluate/system.txt`: the 500–1,000-character recommendation describes each input resume answer, not the length of each generated evaluation field.
- Added a local comparison harness at `python/scripts/compare_evaluate_models.py`; results are written outside the repository under `/private/tmp`.

Verification:
- `cd python && ../.venv/bin/pytest -q` passed: 94 tests, one existing Starlette/httpx deprecation warning.
- Canonical input: `python/scripts/sample_analyze_request.json`, fixed context for provider isolation.
- Reference `analysis_result.json`: 3,827 evaluation text characters; 5,360 including revision text; each `best_reply` 258–274 characters.
- Original prompt EXAONE runs: 2,210 characters with strategy validation failure; 4,464 characters with all stages successful.
- Clarified prompt EXAONE runs: 3,924 and 4,112 characters; axes, fit, improvement, and strategy all succeeded in both runs.

Assessment / remaining:
- Keep staged change 1 provisionally: its average evaluation volume is about 5% above the reference and substantially less variable in this two-run sample.
- Do not claim a reliable failure-rate improvement from two runs.
- Unsupported facts and foreign-script corruption remain, including invented team/tenure and patent/paper judgments. The next proposed isolated change is an axes evidence-grounding rule.
- GPT comparison is blocked by missing `OPENAI_API_KEY`. Historical repository configuration used `gpt-5.4-mini`, which should be the primary GPT comparator when credentials are available.

## 2026-08-13 — EXAONE evaluation output reliability, staged change 2

Goal: constrain applicant claims to input evidence, then measure score and character stability over ten identical EXAONE evaluations.

Changed:
- Expanded the axes grounding rule in `python/resources/prompts/evaluate/system.txt` and added prompt contract assertions.
- Extended `python/scripts/compare_evaluate_models.py` with repeat execution, per-run output capture, stage failures/timing/tokens, score distributions, Unicode corruption detection, unknown Latin-token detection, and risky-claim diagnostics.

Verification:
- Targeted prompt tests: 2 passed.
- Full Python suite: 94 passed, one existing Starlette/httpx deprecation warning.
- Live command: `cd python && ../.venv/bin/python scripts/compare_evaluate_models.py --request scripts/sample_analyze_request.json --providers exaone --runs 10 --label axes-source-grounding-v2-10runs --output /private/tmp/pertineo_exaone_axes_grounding_v2_10runs.json`.
- Scores were identical across all 9 axes successes: x=4.3, y=4.0, z=4.1.
- Full four-stage success: 8/10. One axes and one fit call ended at exactly 4,096 completion tokens with `LengthFinishReasonError`.
- Full-success output volume: mean 3,908 text characters, min 2,555, max 4,659; reference evaluation volume is 3,827.
- Explicit foreign/replacement characters occurred in 2/10 runs. Malformed/unknown Latin fragments occurred in 7/10 runs.
- With identical scores, level was `보통` 7/8 and `높음` 1/8.
- Unsupported auxiliary-role assertions remained in 2 runs, and prohibited absence wording reappeared in downstream improvement output.

Assessment / next approval gate:
- Keep staged change 2 provisionally because scores are stable and normal output volume matches the reference, but prompt grounding alone is insufficient for final output integrity.
- Proposed next isolated change: validate each Evaluate substage for corrupt characters and prohibited unsupported assertions, then retry only that substage once. Do not implement until user approval.

## 2026-08-13 — Structured-output retry diagnostics and current success artifact

Goal: preserve one current successful full result before further behavior changes and make EXAONE retry failures diagnosable from logs.

Changed:
- Added root `result.json`, generated by the live local SSE workflow using `python/scripts/sample_analyze_request.json` before diagnostic logging changes.
- `openai_chat_client.py` now retains raw Friendli responses on structured parsing failures and logs privacy-bounded diagnostics: model/schema/error/finish reason/token counts/prompt and output hashes/bracket balance/repetition/compression/unexpected Unicode/validation paths. Raw head/tail previews are DEBUG-only.
- `engine.py` now records each node attempt, whether it will retry, and successful recovery after a retry.
- Added focused tests for truncated completions, raw Pydantic failures, legacy SDK raw responses, and node retry/recovery logging.

Verification:
- Current success artifact: `failed=false`, x=4.3/y=4.1/z=3.9, level=`높음`, three revised answers, 5,510 evaluation+revision text characters.
- Input SHA-256: `9331fa84d688cfa4af30fe913509d5390d7874ee6b9ec862ade913dc09d7eaa7`; result SHA-256: `bf3c8371351c91f31ca8ddcd7fd5b5d9b10963d911c7b7b71a913b00ad12a146`.
- The current success artifact still contains unsupported facts and a replacement character, so it is diagnostic evidence, not an approved quality baseline.
- Live retry reproduction: two axes attempts both produced z=3.98 and identical 1,077-character output hashes (`b064b2351a21fbdc`), then failed the Python 0.1-increment validator. Each used 413 completion tokens; this was not a length failure.
- Schema inspection: score is exposed to Friendli only as JSON Schema `number`; Python's range/tenth validators do not appear in the generation schema. Arrays and strings also have no model-visible upper bounds.
- Focused logging tests: 8 passed.
- Full Python suite: 97 passed, one existing Starlette/httpx deprecation warning.

Diagnosis / remaining:
- Whole-node deterministic retry without error feedback is ineffective for deterministic schema-value errors and repeats cost/latency.
- Z weighted arithmetic permits hundredths while final output requires tenths, explaining the repeated 3.98.
- Historical 4,096-token failures are a separate constrained-decoding stall: open-ended strings/arrays allow schema-valid repetition until max tokens.
- Next candidate, pending user approval: encode the allowed 1.0–5.0 tenth-step score set as a number enum; separately simplify the axes rubric and add substage-only repair for length/corruption failures.

## 2026-08-13 — Model-visible score enum

Goal: prevent EXAONE from decoding unsupported hundredth-step scores such as 3.98 while preserving float values in the application and public response.

Changed:
- Replaced `AxisEvaluation.score: float` plus a post-generation validator with an inline numeric `Literal` enum containing all 41 values from 1.0 through 5.0 in 0.1 steps.
- Added a schema contract test proving that the number enum is inline, exact, and not represented by an unsupported nested `$ref`.

Verification:
- An initial Python `Enum` implementation was rejected by Friendli before generation with HTTP 422 `Reference not found: #/$defs/AxisScore`; it was not retained.
- The inline enum was accepted by Friendli. Three identical EXAONE runs all generated x=4.3, y=4.2, z=4.1, with zero score variance and no score-validation failure.
- Two of three runs completed all four EVALUATE stages. One failed at `strategy` because an action item contained the prohibited example marker; this is separate from the score schema.
- Full-success evaluation text measured 3,620 and 3,719 characters (mean 3,669.5) versus the 3,827-character reference.
- One of three runs contained Arabic characters in an improvement string, and unsupported-absence assertions remained. The enum does not address corruption or grounding.
- Targeted evaluation tests: 9 passed. Full Python suite: 98 passed with one existing Starlette/httpx deprecation warning. `git diff --check` passed after the harness note updates.

Assessment / next approval gate:
- Keep the inline score enum: it fixes the deterministic 3.98 contract failure without changing token limits, prompt volume, retry policy, or response value types.
- Do not bundle the remaining strategy-validation, Unicode-corruption, unsupported-claim, or level-derivation fixes. Present those measurements and wait for the next user-approved isolated change.

## 2026-08-13 — Score-enum ten-run failure-rate check

Goal: measure the current EXAONE EVALUATE failure rate over ten fresh identical runs after applying the inline score enum.

Execution:
- Input: `python/scripts/sample_analyze_request.json`.
- Context: fixed empty pass-score/web/vector reference context from `compare_evaluate_models.py`.
- Provider/model path: the currently configured Friendli EXAONE deployment.
- Raw report: `/private/tmp/exaone_axis_score_enum_check_10runs.json` (temporary, not a tracked artifact).

Results:
- Pipeline success: 9/10; pipeline failure: 1/10 (10%). The only failed stage was `strategy`, where two generated action-item arrays contained prohibited example wording and failed Pydantic validation.
- Stage failures: axes 0/10, fit 0/10, improvement 0/10, strategy 1/10. There were no length failures and no score validation failures.
- Scores were identical in all ten runs: x=4.3, y=4.2, z=4.1. Every axis had population standard deviation 0 and range 0. All generated levels were `높음`.
- Mean total EVALUATE latency was 12.870 seconds (median 12.281, min 12.076, max 15.613). Mean node times: axes 4.295, fit 1.528, improvement 5.403, strategy 1.645 seconds.
- All nine successful output payloads were byte-identical after canonical JSON serialization and measured 3,608 text characters, 5.7% below the 3,827-character reference.
- Quality-sensitive result: 9/10 runs contained the same three Arabic characters in `improvement.strength[1]`; all 10 runs triggered at least one risky unsupported-claim diagnostic. Therefore transport/schema success is 90%, but strict quality acceptance under the current diagnostics is 0/10.
- The observed 10% failure rate has a wide Wilson 95% interval of approximately 1.8%–40.4%; ten runs are enough to expose the current failure mode but not to estimate production reliability tightly.

Assessment:
- Compared with the preceding ten-run check (8/10 complete), the point failure rate fell from 20% to 10%, and the prior axes/fit length failures were absent. The samples are too small to attribute a statistically reliable improvement to the enum.
- The enum achieved its narrow objective: all ten score stages succeeded and no hundredth-step score appeared. The next isolated issue is deterministic Unicode corruption in the improvement stage, followed separately by strategy example-wording validation.

## 2026-08-13 — Ten-run representative PDF

- Extended `python/scripts/json_to_pdf_report.py` so it can directly normalize a fixed-context comparison report, select the first successful four-stage result, combine its four EVALUATE outputs, and show run-scope/quality notes.
- Missing Schemer data is now shown as `미실행` instead of incorrectly appearing as a validation failure. Existing full-workflow JSON behavior remains unchanged.
- Generated and opened `python/scripts/exaone_enum_10run_evaluation_report.pdf`: 4 pages, approximately 57 KB. It contains the unmodified representative run-1 model response, 9/10 technical success, 12.870-second mean EVALUATE latency, explicit fixed-context/no-Reviser scope, and the 9/10 corruption plus 10/10 risky-claim warnings.
- Installed the already-declared `reportlab>=4.2` script dependency into the local virtual environment; no dependency manifest changed.
- Rendered the first page to an image and visually verified Korean text and report layout before opening the PDF with the system viewer.

## 2026-08-13 — Full workflow report with Schemer and Reviser

Goal: explain the earlier benchmark scope and produce a real full-pipeline artifact that includes Schemer and Reviser results.

Why they were previously excluded:
- The ten-run test isolated the score-enum change inside EVALUATE with fixed pass-score/web/vector context. Running Schemer, live web/data/vector retrieval, and Reviser would introduce unrelated model calls, external latency, context variability, and downstream validation failures, preventing a clean attribution of score-schema behavior.
- The earlier 12.870-second figure is therefore EVALUATE-only and must not be presented as end-to-end latency.

Changed for observability/reporting:
- `run_analyze_to_json.py` now records end-to-end time, event-relative timestamps, approximate node intervals, fallback event types, and vector-context result in its JSON output.
- `EvaluateNode` emits `evaluate_vector_context` with status and selected/document counts; no retrieved content or secret is exposed.
- `json_to_pdf_report.py` now renders full-run scope, fallback, vector-context, Reviser count, and Unicode warning notes while preserving existing full-workflow report content.

Live full workflow result:
- Input: `python/scripts/sample_analyze_request.json`; output JSON: `python/scripts/exaone_full_pipeline_result.json`; output PDF: `python/scripts/exaone_full_pipeline_report.pdf` (6 pages, approximately 73 KB).
- Final workflow completed successfully in 68.635 seconds. Approximate event-based node intervals: SCHEMER 0.631s, WEBSEARCH 1.920s, DATA 1.288s, EVALUATE 54.742s including one full-node retry, REVISE 7.703s. Remaining time is mainly tracing/event boundaries and inter-node overhead.
- Schemer passed question and answer validity without recheck, reason `정상`, track `engineering`.
- EVALUATE first attempt failed in Fit after 4,096 tokens with 99.19% duplicate-sentence ratio and then recovered on the workflow retry. Final scores were x=4.3/y=4.1/z=3.9, level `높음`.
- Vector context returned status `failure`, 0 selected keys and 0 documents because runtime embedding remained configured to OpenAI while no OpenAI key was present. This path is intentionally non-blocking; live web search and DynamoDB pass-score context were still used.
- Reviser returned all three answer/reason/expectation items. Question 2 first generated Thai characters, triggered one item-local `revise_targeted_repair`, and passed on regeneration; no safe original-preserving fallback was used.
- Final Reviser output had no unexpected foreign-script characters, but manual review found malformed prose in answers 1 and 2 (`파이프라인을 설계. 대용량...`, `캐시 정책 개선을 통해. 이를 통해...`). The current validators detect unsupported characters/numbers/tokens and minimum length, not grammar or sentence completeness.
- Final EVALUATE still contained Thai U+0E32/U+0E23 in `skill_fit`, plus unsupported C/C++/Python/Redis claims. Evaluation outputs currently lack the Reviser-style integrity validator.

Verification:
- Focused workflow/Schemer/Reviser/evaluation tests: 22 passed.
- Full Python suite: 98 passed, one existing Starlette/httpx deprecation warning.
- `git diff --check` passed. The PDF first page was visually inspected and the six-page PDF was opened in the system viewer.

## 2026-08-13 — Reviser prompt-strength preservation with output constraints

Goal: retain the persuasive/job-tailored strengths of the earlier Reviser prompt while preventing EXAONE fragments, corruption, unsupported claims, and whole-item loss caused by auxiliary explanation fields.

Changed:
- Reintroduced top-tier full rewriting, source-backed specificity, conclusion/action/result/job linkage, and evaluation strategy names as editing focus. Did not restore the old requirement to invent metrics or experiences.
- Added source preservation for original numbers/Latin tokens and numeric qualifiers, answer length bounds, complete polite Korean sentences, duplicate detection, claim-escalation terms, future-plan strength, and Unicode integrity.
- Isolated best-answer acceptance from explanation quality. Valid answers survive malformed `reply_reason`/`expectation`; only those fields use a deterministic safe explanation and emit `revise_explanation_fallback`.
- Added deterministic restoration for omitted source numeric prefixes such as `약` and `초당`, followed by the full validator, with `revise_numeric_qualifier_restore` observability.
- Retry context now carries only the previous best answer plus answer-specific problems, not malformed explanation text.
- Reporting scripts record the new fallback/restore events.

Rejected iterations:
- An over-constrained candidate caused 9/9 answer items to preserve the original after retries and was not retained.
- Putting numeric-qualifier instructions into the global prompt increased source fallback to 4/9 and was removed; qualifier handling remains local and deterministic.

Live EXAONE evidence:
- Same stored `sample_analyze_request.json` request and evaluation context, three final Reviser runs.
- Success 3/3; latencies 10.481s, 10.051s, 8.295s (mean 9.609s).
- Answer targeted repairs 0, original-answer safe fallbacks 0, numeric qualifier restores 3, explanation fallback events 9.
- All three final answer sets were byte-identical by per-answer SHA-256; lengths 272/258/212 characters on every run.
- All 9 final answer items passed validators and all final answer/reason/expectation fields were free of unexpected scripts.
- Direct GPT-5.4 execution remains unavailable because `OPENAI_API_KEY` is absent. The stored prior result was used only as a qualitative reference; historical configured comparator is `gpt-5.4-mini`, not full GPT-5.4.

Verification:
- Focused Reviser/engine tests: 40 passed.
- Full Python suite: 123 passed, one existing Starlette/httpx deprecation warning.
- Python compile checks and `git diff --check` passed.
- User waived issue creation; branch remains `reviser-output-reliability`; no commit, push, or PR was created.

## 2026-08-12 — Upstage Embed 2 parallel migration path

Goal: prepare a safe, resumable migration from OpenAI `text-embedding-3-small` to Upstage Embed 2 without overwriting the active 1,536-dimensional index.

Workflow:
- The user requested Upstage API integration on branch `embedding-data-export` and continued to waive issue/PR creation.
- Official Upstage documentation established the exact models: `solar-embedding-2-query` and `solar-embedding-2-passage`, dimension 1,024, 8K context, up to 100 inputs and 204,800 total tokens per batch.
- No live Upstage call or S3 mutation was made because `UPSTAGE_API_KEY` is not configured.

Changed:
- Added a validated async Upstage embedding client and provider-selectable query embedding path.
- Kept `EMBEDDING_PROVIDER=openai` as the safe default until the parallel Upstage index is complete and verified.
- Added `tools/reembed_upstage.py` for hash-checked source loading, passage batching, retry/429 handling, adaptive batch splitting, exact 1,024-dimension validation, new-index creation, metadata preservation, resume-by-existing-key, final key reconciliation, token/cost reporting, and failure reporting without silent truncation.
- Added environment examples and migration/rollback instructions.

Verification:
- Baseline `pytest -q tests/test_vector_context_service.py`: 5 passed.
- Targeted Upstage/vector/re-embedding tests: 15 passed.
- Full `cd python && ../.venv/bin/pytest -q`: 82 passed, one existing Starlette/httpx deprecation warning.
- `py_compile` passed for the Upstage client, runtime vector embedder, and re-embedding tool.
- `git diff --check` passed.
- Dry run: 1,991 source records, 6,371,138 characters, max 15,157 characters, 100 estimated batches at batch size 20, target `pertineo-data-vector-upstage-embed2`.

Remaining:
- Add `UPSTAGE_API_KEY` to the ignored `python/.env`, run a one-record API smoke, then run the complete re-embedding command.
- Compare old/new retrieval on representative queries. Only after the generated report has `success=true`, switch `EMBEDDING_PROVIDER=upstage` and `S3_VECTORS_INDEX=pertineo-data-vector-upstage-embed2` together.

## 2026-08-12 — Upstage full re-embedding, A/B, and runtime cutover

Execution:
- Existing target vectors before full run: 1 smoke-test vector.
- Full command uploaded the remaining 1,990 records in 100 batches.
- Elapsed 696.870 seconds; 4,237,818 prompt tokens; list-price equivalent $0.08475636.
- Final report: `success=true`, 1,991 matching vectors, zero failures, zero missing keys, zero extra keys.
- Independent S3 readback confirmed 1,991 unique keys, 1,024 dimensions, passage model/provider metadata, and exact equality with the 1,991 source IDs.

A/B evidence:
- Canonical sample: Upstage 0.199s versus OpenAI 0.555s; exact company occurrence 3/3 versus 2/3; Top-3 overlap 1.
- Twenty frequent company/position queries (60 result slots): Upstage/OpenAI exact company hits 39/32, position hits 10/5, both hits 7/5. Upstage was greater than or equal on company hits in 16/20 queries and both-field hits in 20/20.
- This is an exact-string retrieval proxy without human-labeled relevance judgments.

Runtime fix and smoke:
- Added optional AWS credential settings and explicitly forwarded dotenv credentials to DynamoDB/S3 Vectors clients; empty values still use boto3's default provider chain.
- Moved the interactive Upstage key smoke out of pytest collection into `tools/smoke_upstage_api.py`.
- Switched the ignored local `.env` provider/index pair to Upstage after successful migration and A/B.
- Actual application path succeeded: Upstage query embedding → new S3 Top-3 → three DynamoDB contexts, status `success`, elapsed 0.447s.
- Final full Python suite passed 85 tests with only the existing Starlette/httpx deprecation warning. AWS credential factory tests run with explicit dummy credentials and no live calls.

## 2026-08-12 — User-requested Upstage index removal

- Rolled the ignored local `.env` back to `EMBEDDING_PROVIDER=openai` and `S3_VECTORS_INDEX=pertineo-data-vector-index` before deletion.
- Read-only pre-delete verification confirmed target `pertineo-data-vector-upstage-embed2`, dimension 1,024, float32/cosine, 1,991 vectors, and inactive runtime status.
- Deleted exactly that S3 Vector index; AWS permanently removed its 1,991 vectors and metadata with the index.
- Post-delete `GetIndex` returned NotFound for the target, while existing `pertineo-data-vector-index` remained present at dimension 1,536.
- Git-ignored local exports and migration reports remain, so re-creation is possible only by running the embedding/indexing process again.
## 2026-08-13 — Temporary Upstage S3 Vector full-workflow verification

Goal: upload the saved Upstage 1,024-dimensional vectors to a temporary S3 Vector index, run the complete live workflow with Upstage retrieval, preserve the JSON result, and delete the temporary index afterward.

Workflow:
- User explicitly approved sending the canonical sample through the configured EXAONE/Friendli, Tavily, DynamoDB, Upstage, S3 Vectors, and LangSmith paths.
- No application code or tracked runtime configuration was changed; provider/index selection used process-local environment overrides.
- Branch remained `reviser-output-reliability`; no issue, commit, push, or PR was created for this operational verification.

AWS execution:
- Preflight confirmed the existing `pertineo-data-vector-index` at 1,536 dimensions and the Upstage target absent.
- Created `pertineo-data-vector-upstage-embed2` at 1,024 dimensions, float32/cosine, and uploaded 1,991/1,991 saved Upstage passage vectors in 20 batches.
- Upload reconciliation found zero missing keys, zero extra keys, and zero failures; the upload path did not call an embedding API or DynamoDB.
- Actual application retrieval succeeded: Upstage `solar-embedding-2-query` -> S3 Vector Top-3 -> three DynamoDB document contexts.

Full workflow result:
- Output: `python/scripts/upstage_full_pipeline_result.json`; SHA-256 `b4c9adada25056f29de57020afdb55f19f79d6de4a0b932ed76d4e4caab80d60`.
- Completed successfully in 36.285 seconds with vector context `success` (3 selected keys, 3 documents), no workflow error, scores x=4.3/y=4.1/z=3.9, and level `보통`.
- Three revised answers were returned without unexpected-script characters. Reviser used numeric-qualifier restoration, targeted repair, one safe-original fallback, and one explanation fallback.

Cleanup:
- Stopped the Upstage-configured temporary local server before AWS cleanup.
- Deleted exactly `pertineo-data-vector-upstage-embed2`; post-delete `GetIndex` returned `NotFoundException`.
- Verified the existing `pertineo-data-vector-index` remained present at 1,536 dimensions with 1,991 vectors.
- Local Upstage JSONL and the full-workflow result JSON were retained.

## 2026-08-13 — Deterministic compare score and Reviser 4,096-token verification

Goal: remove model judgment from `compare_score`, raise the per-question Reviser output ceiling from 3,072 to 4,096 tokens, diagnose Reviser failures, and validate both synthetic repeated runs and one live Upstage full workflow.

Workflow:
- The user explicitly withdrew GitHub issue/branch/PR actions for this task. No further GitHub operation, commit, push, or PR was attempted.
- `compare_score` is now computed after the model produces x/y/z applicant scores. Each axis compares the applicant score with the corresponding DynamoDB company/track pass-score average, rounds through `Decimal` to two decimal places, and emits an exact higher/lower/equal sentence. It emits `비교 대상 없음` only when that axis has no baseline.
- The Evaluate prompt now returns the placeholder `코드 계산 예정`; model-produced comparison prose is always overwritten before downstream stages consume the axes result.
- Reviser still runs once per question. Its maximum output is now 4,096 tokens per question rather than one 4,096-token budget shared by all three questions.
- Added focused comparison/token contract tests and benchmark reporting for comparison strings and the effective Reviser token ceiling.

Ten-run synthetic EXAONE verification:
- Command: `cd python && ../.venv/bin/python scripts/benchmark_exaone_pipeline_consistency.py --runs 10 --output /private/tmp/exaone_compare_score_reviser_4096_synthetic_10runs.json`.
- Result: 10/10 workflows completed, zero final-validator problems, zero cross-question leakage, and all 30 comparison statements were arithmetically correct for their generated applicant scores and fixed x=4.0/y=3.9/z=4.1 baselines.
- Mean end-to-end time was 22.275 seconds (median 21.714, min 19.962, max 29.125).
- Reviser observed 12 targeted repairs, 10 safe-original fallbacks, and one explanation fallback. Question 2 was safely preserved in 9/10 runs; one run accepted a revised answer.
- Repeated rejection causes were unsupported new actions (`도입`, `운영`, `병목`, `최적화`), changed numbers (`850ms` to `85ms`), omitted numeric expressions/qualifiers, incomplete sentence fragments, unexpected script characters, and future-plan wording strengthened into a definite promise.
- No call ended by length/max-token exhaustion. The evidence does not support the hypothesis that the earlier question-2 fallback was caused by the 3,072-token ceiling.

Live Upstage full workflow:
- Recreated temporary index `pertineo-data-vector-upstage-embed2`, uploaded and reconciled 1,991/1,991 locally saved Upstage passage vectors at 1,024 dimensions, then used process-local `EMBEDDING_PROVIDER=upstage` and index overrides.
- Output: `python/scripts/upstage_compare_score_reviser_4096_result.json`; SHA-256 `7742dee92912f7b1c5924bb246c963a8601888a3192d847ec62ec5953cd508c0`.
- Completed with HTTP 200 and `failed=false` in 41.965 seconds. Upstage query embedding returned HTTP 200; S3 Top-3 selected three keys and DynamoDB resolved all three documents.
- Applicant scores x=4.2/y=4.1/z=3.9 were compared in code with pass averages x=4.2/y=4.1/z=3.98, producing exact equal/equal/0.08-lower statements. A separate assertion recomputed the three values with the production helper and matched the saved JSON.
- Reviser returned all three answer/reason/expectation items. Question 2 attempts used 269 and 403 completion tokens; they failed because of invented `도입`/`최적화` wording and loss of `6개월`/`6개월 간`, not token exhaustion. Question 3 strengthened a plan into a definite promise. Safe fallback preserved both source answers.
- Structural output passed, but the Evaluate prose is not quality-approved: one basis item contains Japanese `もの` (U+3082/U+306E), and manual review found malformed `M moments` and `인과되` phrases. The final Reviser payload contains no unexpected-script code under the existing detector.
- The temporary Upstage index was deleted after the server stopped. Post-delete lookup returned not found; the existing `pertineo-data-vector-index` remains 1,536-dimensional with 1,991 vectors.

Verification:
- Actual JSON assertions passed: workflow success, vector context 3/3, three complete Reviser items, terminal `revise_result`/`final_state`/`workflow_completed` events, and code-exact comparison text.
- Full Python suite: 126 passed with one existing Starlette/httpx deprecation warning.
- `git diff --check` passed.
- A controlled ten-run replay of the stored real resume sample was not executed because the execution approval gate required explicit permission to resend that resume-derived content to Friendli ten times. The completed ten-run result uses fully synthetic applicant and retrieval context; the live stored sample was run once.

## 2026-08-13 — Reviser strategy application and seven-attempt latency evaluation

Goal: prevent EXAONE Reviser from accepting unchanged or near-copy answers, apply earlier Evaluate strategy safely, and measure the quality/latency tradeoff of up to seven per-question attempts.

Workflow:
- The user continued to waive issue/PR creation and approved repeated live EXAONE calls for the saved canonical synthetic sample.
- Branch remained `reviser-output-reliability`; no commit, push, or PR was created.

Changed:
- Compiled Evaluate strategy names/action items into source-grounded editing operations instead of exposing unsafe raw action details.
- Added deterministic exact-copy and >0.92 near-copy rejection for generated candidates while retaining explicit safe-original fallback validation.
- Added model-visible forbidden claim terms, source-grounded study-group wording handling, and five then seven maximum per-question attempts at the user's request.
- Used deterministic non-reasoning first generation and LG-recommended sampled non-reasoning correction calls (`temperature=1.0`, `top_p=0.95`).
- Extended the Reviser benchmark with per-answer similarities, actual candidate call counts, per-run latency, p95, and seconds per call.
- Added Markdown/PDF report generation and preserved all measured comparison JSON files.

Measured result:
- Stored pre-change artifact: 0/3 answers changed; two safe-original fallbacks; Reviser 13.869s.
- Sampled five-attempt intermediate: 11/15 changed (73.3%), four fallbacks, 44 repairs, mean 28.221s.
- Retained hybrid five-attempt: 13/15 changed (86.7%), two fallbacks, 32 repairs, mean 24.886s, p95 26.422s.
- Final seven-attempt/seven-run: 7/7 technical success, 19/21 changed (90.5%), two fallbacks, 45 repairs, mean 25.437s, median 22.450s, p95 38.755s, max 42.859s, 66 candidate calls total.
- Manual audit found at least five semantic attribution risks despite structural validation: shifted six-month scope, invented Samsung internship attribution, and stronger company-role wording. Treat 90.5% as structural revision rate, not final prose approval.
- Final user decision: keep the production per-question ceiling at five attempts. Seven-attempt data remains comparison-only because it improved structural revision by 3.8 percentage points but raised p95 from 26.422s to 38.755s and still produced two fallbacks.

Verification:
- Focused Reviser/OpenAI-client tests: 46 passed before the final seven-attempt run.
- Final full Python suite: 131 passed with one existing Starlette/httpx deprecation warning.
- Benchmark script and report generator compile checks passed.
- PDF report rendered successfully with Korean fonts and comparison table.
- `git diff --check` passed before final full-suite verification.
- After fixing the production ceiling at five, the full Python suite still passed 131 tests; report regeneration, Python compile, feature JSON validation, and `git diff --check` also passed without new live model calls.

Artifacts:
- `python/scripts/reviser_strategy_revision_7attempts_7runs.json`
- `python/scripts/reviser_strategy_revision_report.md`
- `python/scripts/reviser_strategy_revision_report.pdf`

Remaining risk:
- Repeated attempts do not reliably repair semantic scope/attribution errors and can push tail latency above 40 seconds. Sentence-level fact ownership and numeric-modifier validation should be the next isolated change.
