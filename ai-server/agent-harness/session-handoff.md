# Session Handoff

## Current Objective — 2026-08-29

Preserve the completed live verification of the data-backed company
recommendation v1 and isolate posting-quality hardening as the next change.

## Current Status — 2026-08-29

- Branch: `feature/data-backed-company-recommendations`, based on the OpenAI
  provider-unification branch. The user's existing issue-first waiver was
  continued; no issue/PR exists.
- Implementation commit: `80321a2` (`Lore: rank companies with historical
  success evidence`).
- `POST /api/career/company-recommendations` is implemented with role evidence,
  X/Y/Z assessment, DynamoDB company/track aggregation, a default ten-sample
  floor, DB-first candidate selection, active-job verification, and a
  deterministic 50/40/10 score.
- Full verification: 162 Python tests passed; compile and diff checks passed.
- Live read-only DynamoDB preflight succeeded: engineering n>=10 returned 38
  eligible companies and 1,866 samples.
- `python/.env` was loaded with Uvicorn dotenv support. The current feature
  branch is running on `127.0.0.1:8080` as PID 87037.
- The synthetic live request returned HTTP 200 in 43.110 seconds. OpenAI,
  DynamoDB, and Tavily participated; the response contained three distinct
  companies and internally consistent overall score sums.
- Result artifact:
  `/private/tmp/pertineo-company-recommendation-live.json` (SHA-256
  `dab9f3d057cd6f3ae11e40e7a4ea1538590aedb8ada35652ed5659483e08b9b5`).
- Quality caveat: all selected postings had zero role-match contribution and no
  extracted requirements. LG Electronics was paired with an LG partner-company
  page, so the company identity check failed despite `verified_active`.

## Resume Steps — 2026-08-29

1. If posting-quality work is requested, make it a separate issue/branch unless
   the user continues the existing waiver.
2. Require exact normalized company identity, a concrete role/title, positive
   role-match evidence, and extracted requirements before accepting a posting.
3. Add mocked regression tests for generic recruiting pages and subsidiaries or
   partner-company false positives, then repeat the synthetic live request.

## Previous Objective

Adapt EXAONE evaluation/revision output one isolated prompt change at a time, preserving the information volume of `python/scripts/analysis_result.json` and comparing each stage before keeping or rejecting it.

## Previous Status

- Branch: `reviser-output-reliability`, tracking `origin/reviser-output-reliability`.
- Staged change 1 clarifies that the 500–1,000-character guideline applies to each input answer, not generated output fields.
- Reference output volume is 3,827 evaluation text characters and 5,360 with Reviser; staged-change EXAONE evaluations measured 3,924 and 4,112 characters.
- Staged change 1 is provisionally retained. It does not fix invented facts or foreign-script corruption.
- Staged change 2 constrains applicant facts to explicit input evidence. Ten-run EXAONE results had perfectly stable generated scores (4.3/4.0/4.1), 8/10 full-stage success, 2/10 explicit Unicode corruption, and 7/10 malformed/unknown Latin fragments. Same-score level remained inconsistent (7 `보통`, 1 `높음`).
- GPT comparison cannot run until `OPENAI_API_KEY` is available. Use historical `gpt-5.4-mini` as the primary comparator, with full GPT-5.4 only as a secondary comparison if desired.
- `python/scripts/compare_evaluate_models.py` is untracked, and the prompt plus harness notes are uncommitted.
- Root `result.json` is the requested current successful artifact produced before retry-logging changes. It is schema-valid and `failed=false`, but contains unsupported generated facts and `�`; do not present it as quality-approved.
- Structured-output failure logging now captures raw completion diagnostics and workflow retry attempts. A live reproduction showed identical z=3.98 output on both deterministic retries because the model-visible schema accepts any number while Python later requires 0.1 increments.
- Score is now an inline model-visible number enum with all 41 tenth-step values from 1.0 through 5.0. Three live EXAONE runs generated identical 4.3/4.2/4.1 scores; the prior 3.98 path is no longer decodable. A Python Enum `$ref` variant was rejected by Friendli and was replaced with an inline Literal enum.
- A fresh ten-run enum check completed 9/10 pipelines (10% technical failure); only strategy failed once on prohibited example wording. All ten scores were exactly 4.3/4.2/4.1, but 9/10 runs repeated the same Arabic corruption and all ten triggered unsupported-claim diagnostics, so strict diagnostic quality acceptance was 0/10.
- `python/scripts/exaone_enum_10run_evaluation_report.pdf` is the opened 4-page representative report for that ten-run check. It includes the raw successful EVALUATE response and scope/quality warnings; no Reviser output is present because the benchmark did not run Reviser.
- A real full workflow run is saved as `python/scripts/exaone_full_pipeline_result.json` and opened as `python/scripts/exaone_full_pipeline_report.pdf`. It completed in 68.635s: Schemer passed; EVALUATE retried after a 4,096-token Fit repetition; Reviser repaired Thai corruption in item 2 and returned three results. Vector context was unavailable because runtime still selected OpenAI embeddings without an OpenAI key. Final Reviser text is foreign-character clean but has malformed sentence joins; final EVALUATE still contains Thai characters and unsupported technical claims.
- Reviser now preserves the earlier prompt's persuasive rewrite intent while enforcing source-backed output. Answer validation is separate from explanation validation, malformed explanations use field-only fallback, source numeric prefixes are deterministically restored, and retries carry only the prior answer plus answer errors.
- Final same-input EXAONE Reviser check: 3/3 success; mean 9.609s; 0 answer retries; 0 original-answer fallbacks; 3 numeric-prefix restores; 9 explanation fallback events. All three answer sets were byte-identical and all 9 items passed validation without unexpected scripts.
- `compare_score` is no longer model-authored. Production code computes higher/lower/equal text from each generated applicant axis score and its DynamoDB company/track pass-score average; missing baselines alone produce `비교 대상 없음`.
- Reviser now has a 4,096-token maximum for each isolated question call. Ten synthetic full-pipeline runs completed 10/10, but used 10 safe-original fallbacks. Observed failures were semantic preservation and output-integrity failures, not token exhaustion.
- Latest live result is `python/scripts/upstage_compare_score_reviser_4096_result.json` (SHA-256 `7742dee92912f7b1c5924bb246c963a8601888a3192d847ec62ec5953cd508c0`): `failed=false`, Upstage vector context 3/3, code-exact compare scores, and three Reviser items.
- The same live result is structurally complete but not strict prose-quality approved: Evaluate contains Japanese `もの` plus malformed `M moments`/`인과되` text. Reviser output has no unexpected-script code.
- Exported 1,991 source records and 1,991 current vectors under Git-ignored `private_exports/`.
- Upstage Embed 2 query integration and resumable passage re-embedding tool are implemented.
- Upstage migration code and private reports remain locally, but the AWS Upstage index and its 1,991 vectors were deleted at user request.
- A fresh local-only Upstage export now exists at `private_exports/embedding_data_20260812/upstage_vectors.jsonl`: 1,991 unique vectors, 1,024 dimensions, SHA-256 `35d312afeecd82347105b3c1b19bdbb7c32384a4929bef77fd28741c0661392f`.
- Local exact-cosine A/B reports are stored beside the vectors as `embedding_comparison.md` and `embedding_comparison_report.json`. The cleaned 19-query proxy set favored Upstage overall, but human labels and downstream EXAONE evaluation are still missing.
- `python/tools/upload_local_vectors.py` can upload only the saved Upstage JSONL with resume/final-key verification; it does not call embedding APIs or DynamoDB. The latest temporary live upload reconciled 1,991/1,991 and was deleted after full-flow verification.
- Ignored local `.env` is rolled back to the paired OpenAI provider/index settings.
- Existing OpenAI S3 Vector index remains present at dimension 1,536.
- Reviser now receives source-grounded editing operations compiled from Evaluate strategy, rejects exact/near copies in Python, uses deterministic first generation plus sampled correction calls, and allows at most five attempts per question.
- Comparison-only seven-run EXAONE result: 7/7 technical success, 19/21 structurally revised answers, two safe-original fallbacks, mean 25.437s, p95 38.755s, max 42.859s. Manual review still found at least five semantic attribution risks, so this is not final prose-quality approval.
- Comparison artifacts are `python/scripts/reviser_strategy_revision_report.md`, `.pdf`, and `reviser_strategy_revision_7attempts_7runs.json`.

## Previous Resume Steps

1. The user selected the five-attempt ceiling after reviewing the seven-attempt tail-latency tradeoff; keep the seven-run artifact only as comparison evidence.
2. Treat semantic preservation failures separately from token limits: add sentence-level ownership checks for company versus applicant facts and numeric modifier scope before further prompt expansion.
3. If a replay of non-synthetic resume content is required, obtain explicit approval for its exact repeat count before resending it to Friendli.
4. Separately simplify the axes prompt and add substage-only correction for length/corruption failures; re-run fixed-context evaluations after each isolated change.
5. Address deterministic `level` derivation as a separate later change after agreeing score thresholds.

## Files Owned By Harness Work

- `AGENTS.md`
- `docs/agent-harness.md`
- `agent-harness/feature_list.json`
- `agent-harness/progress.md`
- `agent-harness/session-handoff.md`
- `init.sh`

## Files Changed To Fix Baseline

- `src/main/java/pertineo/agent/repository/PreviousResumeDataRepository.java`
- `src/main/java/pertineo/agent/repository/DynamoDbPreviousResumeDataRepository.java`
- `src/main/resources/application-local.yml`

## Last Verification Output

- Local-only Upstage re-embedding passed 1,991/1,991 with zero failures and no AWS access; JSONL validation confirmed all 1,991 unique keys at dimension 1,024.
- Post-delete verification: Upstage target NotFound; existing OpenAI index present at dimension 1,536.
- Final Python suite: 131 passed, one existing deprecation warning. Reviser comparison artifacts, Python compile checks, JSON validation, and `git diff --check` passed.

## Known Risks

- The active OpenAI index is 1,536-dimensional; Upstage Embed 2 is 1,024-dimensional. Never mix provider and index settings.
- The AWS key exposed in a test failure must be rotated before treating the environment as secure.
- `.DS_Store` is unrelated and remains untracked.
