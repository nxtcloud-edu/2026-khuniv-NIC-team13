# AGENTS.md — Pertineo AI Agent Harness

Pertineo AI 2.0 is a Java 21 / Spring Boot service that runs a resume-analysis workflow with OpenAI, Tavily web search, DynamoDB, S3 Vectors, local prompt resources, and SSE streaming APIs.

## Startup Workflow

Before changing code:
1. Read this file.
2. Read `docs/agent-harness.md` for architecture, scope, verification, and handoff rules.
3. Check `agent-harness/progress.md` for current session state and blockers.
4. Check `agent-harness/feature_list.json` before starting feature work.
5. Run the smallest relevant verification command before and after edits.

## Project Map

- App entry: `src/main/java/pertineo/agent/AgentApplication.java`
- API layer: `src/main/java/pertineo/agent/controller/`
- Request/response DTOs: `src/main/java/pertineo/agent/controller/dto/`
- Workflow engine/nodes: `src/main/java/pertineo/agent/workflow/`
- Repository adapters: `src/main/java/pertineo/agent/repository/`
- Vector/search integrations: `src/main/java/pertineo/agent/vector/`, `src/main/java/pertineo/agent/cache/`
- Config/properties: `src/main/java/pertineo/agent/config/`
- Prompt/domain resources: `src/main/resources/`
- Tests: `src/test/java/`

## Working Rules

- Start every code change by creating a GitHub issue from the matching `.github/ISSUE_TEMPLATE/` form, then switch to the issue branch before editing. Use the branch field from the issue template and keep one feature or bugfix per branch.
- When work is complete, open a PR using `.github/PULL_REQUEST_TEMPLATE.md` and match its sections exactly: linked issue, work summary, and optional review requests.
- Issue and PR titles/bodies must not mention assistant/tool-name branding; scan the text before publishing and remove any such wording.
- One feature or bugfix at a time. Update `agent-harness/feature_list.json` when status changes.
- Do not mix refactor with behavior change unless needed for safe implementation.
- Preserve public API routes unless task explicitly changes contract.
- Keep secrets out of files. Use env vars from `application-*.yml`.
- Prefer constructor injection, immutable DTOs/records where practical, and explicit config properties.
- Do not add dependencies without clear need and verification.
- Keep prompt/resource edits small; record changed prompt files in progress notes.
- If DynamoDB/OpenAI/Tavily/S3 Vectors behavior changes, add or update tests with mocks/fakes first.

## Verification Commands

Use smallest proof first:

```bash
./gradlew test
./gradlew build
./init.sh
# Completion smoke hook for live local stack/SSE contract:
scripts/verify_analyze_stream_smoke.sh
```

Notes:
- `./gradlew test` is default for Java behavior changes.
- `./gradlew build` is required before broad completion claims.
- When all work is complete and live local verification is needed, run `scripts/verify_analyze_stream_smoke.sh`; it executes `docker compose up -d --build`, waits for `localhost:8080`, then POSTs the canonical sample payload to `/api/agent/analyze/stream` and requires HTTP 200.
- Treat `scripts/verify_analyze_stream_smoke.sh` as an optional completion hook, not a unit test: it needs Docker, `.env.dev`, and any live integration credentials required by the compose profile.
- Integration behavior that needs external services must be mocked/faked in tests unless task explicitly requires live integration.

## Definition of Done

A change is done when:
- [ ] GitHub issue exists, the working branch matches the issue branch, and the eventual PR body follows `.github/PULL_REQUEST_TEMPLATE.md`.
- [ ] Code/resources updated for one clear scope.
- [ ] Tests or next-best checks pass.
- [ ] Verification evidence recorded in `agent-harness/progress.md`.
- [ ] `agent-harness/feature_list.json` reflects status/evidence for feature work.
- [ ] Known risks, blockers, and not-tested gaps are explicit.
- [ ] Repository can be resumed by a new agent from this harness.

## End of Session

Before ending a coding session:
1. Update `agent-harness/progress.md` with summary, files touched, tests run, issue/branch/PR status, and next step.
2. Update `agent-harness/session-handoff.md` if work remains.
3. Keep git status explainable. Do not overwrite unrelated user changes.
4. Use Lore-style commit messages when committing.
5. If opening a PR, use `.github/PULL_REQUEST_TEMPLATE.md`, link the issue, and remove assistant/tool-name branding from every title/body field.
