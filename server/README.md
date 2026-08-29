# AI Rookie Server

AI Rookie version of the Pertineo backend.

This repository is currently used to rebuild the existing Pertineo backend system in FastAPI.

## Current Status

```txt
older/
  Legacy Spring Boot backend reference.
  Do not modify unless explicitly instructed.

app/
  Target FastAPI application directory.
  Created during FastAPI implementation stages.

tests/
  Target backend test directory.
```

## Goal

Rebuild the existing backend behavior in FastAPI while keeping the legacy Spring Boot code under `older/` as a reference.

The migration is not a Java-to-Python file-by-file translation. The goal is to re-implement backend behavior in a clean FastAPI structure.

## Initial FastAPI Structure

Expected structure:

```txt
app/
  main.py
  api/
  schemas/
  services/
  repositories/
  core/
  integrations/
  db/

tests/
```

## Development

Install dependencies after the FastAPI project files are added:

```bash
pip install -e '.[dev]'
```

Run tests:

```bash
pytest -q
```

Run the API locally:

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

## Notes

- `older/` is reference-only unless explicitly instructed otherwise.
- Keep secrets in environment variables, not in code.
- Do not log raw personal or sensitive data.
