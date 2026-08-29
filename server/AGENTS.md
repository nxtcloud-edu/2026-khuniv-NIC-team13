# AGENTS.md

This file contains minimal agent instructions for this repository.

## Project

This repository is for the AI Rookie version of the Pertineo backend.

The current goal is to rebuild the existing backend behavior in FastAPI.

The legacy Spring Boot backend lives under:

```txt
older/
```

Treat `older/` as reference-only unless explicitly instructed otherwise.

## Development Rules

- Prefer simple, maintainable FastAPI structure.
- Keep route handlers thin.
- Put business logic in `app/services`.
- Put request/response models in `app/schemas`.
- Put persistence access behind repository interfaces in `app/repositories`.
- Put external system integrations in `app/integrations`.
- Put app configuration, middleware, logging, and errors in `app/core`.
- Do not hardcode secrets.
- Do not log raw personal or sensitive data.
- Do not modify `older/` unless explicitly instructed.

## Verification

Before reporting implementation completion, run the relevant checks.

Minimum:

```bash
pytest -q
```

When configured:

```bash
ruff check .
pytest --cov=app --cov-report=term-missing
mypy app
bandit -r app
```

If a command cannot be run, report why instead of inventing results.

## Commit Types

Use concise commit messages with these types when appropriate:

```txt
feat
fix
docs
test
refactor
chore
build
ci
```
