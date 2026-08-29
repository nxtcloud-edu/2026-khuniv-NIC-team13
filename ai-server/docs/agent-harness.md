# Pertineo AI Agent Harness

This document is the detailed operating guide for AI coding agents working on this repository.

## Five-Subsystem Harness

### 1. Instructions

Primary routing file: `AGENTS.md`.

Use this document for details that do not belong in the short routing layer:
- architecture map
- GitHub issue/branch/PR workflow
- verification workflow
- scope boundaries
- session continuity
- feature tracking

### 2. State

State files live under `agent-harness/`:

- `feature_list.json`: feature and task state tracker
- `progress.md`: chronological session log
- `session-handoff.md`: restart packet for unfinished work

Rules:
- Update state after meaningful progress, not after every small edit.
- Record the GitHub issue number, branch name, and PR URL/status when they exist.
- Keep evidence short and concrete: command, result, date, remaining gap.
- Do not store secrets, generated build output, or derivable code summaries as memory.

### 3. GitHub Workflow

Start-of-work rules:
1. Choose the matching issue template under `.github/ISSUE_TEMPLATE/`: `task-issue-form.yml` for normal work, `bug-issue-form.yml` for defects, and `epic-issue-form.yml` only for broad product scope.
2. Create the GitHub issue before code edits. Fill the template fields, including `templateTag`, `branch`, and the details/tasks section.
3. Switch to the issue branch before changing code. If automation creates a Jira-prefixed branch, use that branch; otherwise create a branch whose suffix matches the template branch field.
4. Record the issue and branch in `agent-harness/progress.md`.

Completion rules:
1. Commit only the current task scope. Keep unrelated pre-existing changes out of the branch/PR.
2. Open the PR using `.github/PULL_REQUEST_TEMPLATE.md` and keep its sections: linked issue, work summary, and optional review requests.
3. PR and issue titles/bodies must not include assistant/tool-name branding. Check the final text before publishing.
4. Record the PR URL/status and verification evidence in `agent-harness/progress.md`.

### 4. Verification

Default verification ladder:

1. Targeted unit test for changed class/behavior.
2. `./gradlew test` for normal backend changes.
3. `./gradlew build` before broad completion claims.
4. Manual/API smoke only when behavior is not covered by tests; record exact request and result.
5. Completion hook for live local stack/SSE contract: `scripts/verify_analyze_stream_smoke.sh`. This runs `docker compose up -d --build`, waits for `localhost:8080`, POSTs the canonical 삼성/IT sample payload to `/api/agent/analyze/stream`, and passes only on HTTP 200.

Current project test anchors:
- Spring context smoke: `AgentApplicationTests`
- DynamoDB repository behavior: `DynamoDbPreviousResumeDataRepositoryTest`

External integrations:
- OpenAI, Tavily, DynamoDB, and S3 Vectors must be mocked/faked in tests unless task explicitly requires live integration.
- Local profile reads environment variables. Use dummy values in tests when possible.

### 5. Scope Control

Default scope policy:
- One feature/bug/refactor per session branch.
- Avoid broad package reshuffles unless requested.
- Behavior changes require test evidence.
- Refactors should preserve API contract and prompt semantics unless task says otherwise.

Scope escalation triggers:
- public route changes
- prompt format changes affecting model output
- persistence schema/table changes
- external dependency changes
- destructive data operations

### 6. Lifecycle

Startup:
1. Read `AGENTS.md`.
2. Read `agent-harness/progress.md` latest section.
3. Inspect `agent-harness/feature_list.json` if doing feature work.
4. Create a GitHub issue from the matching `.github/ISSUE_TEMPLATE/` form and switch to the issue branch before editing code.
5. Run a targeted check or `./gradlew test` when baseline confidence matters.

Shutdown:
1. Record summary/evidence plus issue/branch/PR status in `progress.md`.
2. Update feature status/evidence.
3. Fill `session-handoff.md` if incomplete.
4. For completed work, open or prepare the PR with `.github/PULL_REQUEST_TEMPLATE.md` and verify no assistant/tool-name branding remains in the issue/PR text.
5. Leave next agent with exact commands and risks.

## Architecture Notes

Request flow:
1. `AgentController` receives `/api/agent/analyze/stream` request.
2. Request DTO fields populate `AgentState`.
3. `StateGraphEngine` runs workflow asynchronously and streams SSE events.
4. Workflow nodes gather data, search web/vector stores, evaluate, revise, and emit outputs.
5. Repository/config layers isolate DynamoDB and external API settings.

Primary risks:
- long-running SSE timeout and async error handling
- prompt/resource edits changing model output silently
- external services making tests flaky
- local/prod profile drift
- repository methods scanning DynamoDB pages incorrectly

## Quality Bar

Prefer:
- small explicit methods
- domain names over generic names
- tests around workflow/repository edge cases
- config through typed properties
- prompt changes with before/after examples

Avoid:
- hidden network calls in unit tests
- committing `.env*` secrets
- mixing Korean/English domain terms without reason
- broad AI-generated abstractions not used by current code
