import argparse
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "docs" / "pertino-evaluation-dataset-flat.jsonl"
DEFAULT_GRADER = ROOT / "docs" / "pertino-evaluation-python-grader.py"
RESOURCES = ROOT / "src" / "main" / "resources"
API_BASE = "https://api.openai.com/v1"


OUTPUT_SCHEMA_INSTRUCTION = """

You must return only valid JSON. Do not return Markdown, code fences, or text outside JSON.
The JSON must follow this shape:
{
  "x": {
    "score": 0.0,
    "criteria": ["string"],
    "basis": ["string"],
    "summary": "string",
    "compareScore": "string"
  },
  "y": {
    "score": 0.0,
    "criteria": ["string"],
    "basis": ["string"],
    "summary": "string",
    "compareScore": "string"
  },
  "z": {
    "score": 0.0,
    "criteria": ["string"],
    "basis": ["string"],
    "summary": "string",
    "compareScore": "string"
  },
  "roleFit": "string",
  "domainFit": "string",
  "cultureFit": "string",
  "skillFit": "string",
  "compareProb": ["string"],
  "scoreSummary": ["string"],
  "level": "매우 높음 | 높음 | 보통 | 낮음 | 매우 낮음",
  "jobSummary": "string",
  "overall": "string",
  "strength": ["string"],
  "weakness": ["string"],
  "advice": ["string"],
  "improveOverall": ["string"],
  "improveStrategy": [
    {
      "strategyName": "string",
      "actionItems": ["string"]
    }
  ],
  "improveExpectation": ["string"]
}
"""


ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "resume_text": {"type": "string"},
        "questions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "answers": {
            "type": "array",
            "items": {"type": "string"},
        },
        "company": {"type": ["string", "null"]},
        "position": {"type": ["string", "null"]},
        "track": {"type": ["string", "null"]},
        "expected_x": {"type": "number"},
        "expected_y": {"type": "number"},
        "expected_z": {"type": "number"},
        "expected_overall": {"type": "number"},
        "quality_label": {"type": "string"},
        "tier": {"type": "string"},
        "file_name": {"type": "string"},
        "file_type": {"type": "string"},
    },
    "required": [
        "id",
        "resume_text",
        "questions",
        "answers",
        "expected_x",
        "expected_y",
        "expected_z",
        "expected_overall",
        "quality_label",
    ],
}


def request_json(method: str, path: str, api_key: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed: HTTP {error.code}\n{body}") from error


def upload_file(path: Path, api_key: str) -> dict:
    boundary = f"----pertino-{uuid4().hex}"
    file_bytes = path.read_bytes()
    parts = [
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="purpose"\r\n\r\n'
            "evals\r\n"
        ).encode("utf-8"),
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
            "Content-Type: application/jsonl\r\n\r\n"
        ).encode("utf-8"),
        file_bytes,
        f"\r\n--{boundary}--\r\n".encode("utf-8"),
    ]
    body = b"".join(parts)
    request = urllib.request.Request(
        f"{API_BASE}/files",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"POST /files failed: HTTP {error.code}\n{body}") from error


def wait_for_file(file_id: str, api_key: str) -> dict:
    for _ in range(24):
        file_info = request_json("GET", f"/files/{file_id}", api_key)
        if file_info.get("status") == "processed":
            return file_info
        if file_info.get("status") == "error":
            raise RuntimeError(f"File processing failed: {file_info}")
        time.sleep(2)
    raise RuntimeError(f"Timed out waiting for file {file_id} to process")


def count_jsonl_rows(path: Path) -> int:
    rows = 0
    with path.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                json.loads(line)
                rows += 1
    return rows


def prepare_dataset_for_evals(path: Path) -> tuple[Path, bool]:
    """Evals file rows must be shaped as {"item": {...}}.

    The dashboard-friendly flat JSONL keeps each row as the item itself, so this
    wraps rows at upload time without changing the source dataset file.
    """
    needs_wrapping = False
    rows = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            row = json.loads(line)
            if not (isinstance(row, dict) and isinstance(row.get("item"), dict)):
                needs_wrapping = True
                row = {"item": row}
            rows.append(row)

    if not needs_wrapping:
        return path, False

    temp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".jsonl",
        prefix="pertino-evals-upload-",
        delete=False,
    )
    with temp:
        for row in rows:
            temp.write(json.dumps(row, ensure_ascii=False) + "\n")
    return Path(temp.name), True


def read_resource(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def build_eval_prompts() -> str:
    base = read_resource(RESOURCES / "3D_Eval_Prompt_v2.txt")
    business = read_resource(RESOURCES / "track" / "business.txt")
    engineering = read_resource(RESOURCES / "track" / "engineering.txt")
    return (
        f"{base}\n\n"
        "아래 track별 세부 기준 중 Dataset item의 track 값에 맞는 기준을 적용하라.\n"
        "track이 business면 Business Track 기준을 적용하고, engineering이면 Engineering Track 기준을 적용하라.\n\n"
        f"{business}\n\n{engineering}"
    )


def build_messages() -> list[dict[str, str]]:
    system_prompt = read_resource(RESOURCES / "prompts" / "evaluate" / "system.txt")
    user_prompt = read_resource(RESOURCES / "prompts" / "evaluate" / "user.txt")

    system_prompt = system_prompt.replace("{eval_prompts}", build_eval_prompts())
    system_prompt = system_prompt.replace("{position}", "{{ item.position }}")
    system_prompt = system_prompt.replace("{company}", "{{ item.company }}")
    system_prompt = system_prompt.replace("{web_search}", "수집된 기업 정보 없음")
    system_prompt = system_prompt.replace("{pass_score}", "합격자 데이터 없음")
    system_prompt += OUTPUT_SCHEMA_INSTRUCTION

    user_prompt = user_prompt.replace("{applicant_info}", "{}")
    user_prompt = user_prompt.replace("{questions}", "{{ item.questions }}")
    user_prompt = user_prompt.replace("{answers}", "{{ item.answers }}")

    return [
        {"role": "developer", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def create_eval(api_key: str, name: str, grader_source: str) -> dict:
    return request_json(
        "POST",
        "/evals",
        api_key,
        {
            "name": name,
            "data_source_config": {
                "type": "custom",
                "item_schema": ITEM_SCHEMA,
                "include_sample_schema": True,
            },
            "testing_criteria": [
                {
                    "type": "python",
                    "name": "Human score agreement",
                    "source": grader_source,
                    "pass_threshold": 0.75,
                }
            ],
            "metadata": {"project": "pertino", "dataset": DEFAULT_DATASET.name},
        },
    )


def create_run(api_key: str, eval_id: str, file_id: str, model: str, name: str) -> dict:
    return request_json(
        "POST",
        f"/evals/{urllib.parse.quote(eval_id)}/runs",
        api_key,
        {
            "name": name,
            "data_source": {
                "type": "responses",
                "model": model,
                "input_messages": {
                    "type": "template",
                    "template": build_messages(),
                },
                "source": {"type": "file_id", "id": file_id},
                "sampling_params": {
                    "max_completions_tokens": 800,
                    "top_p": 1,
                },
            },
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create and run the Pertineo human-score agreement eval.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--grader", type=Path, default=DEFAULT_GRADER)
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--name", default="Pertineo human score agreement")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY environment variable is required.", file=sys.stderr)
        return 2

    dataset = args.dataset.resolve()
    grader = args.grader.resolve()
    if not dataset.exists():
        print(f"Dataset not found: {dataset}", file=sys.stderr)
        return 2
    if not grader.exists():
        print(f"Grader not found: {grader}", file=sys.stderr)
        return 2

    row_count = count_jsonl_rows(dataset)
    grader_source = grader.read_text(encoding="utf-8")

    upload_dataset, is_temp_dataset = prepare_dataset_for_evals(dataset)

    print(f"Uploading dataset: {dataset} ({row_count} rows)")
    if is_temp_dataset:
        print("Wrapped flat JSONL rows as {'item': ...} for the Evals API upload.")
    file_info = upload_file(upload_dataset, api_key)
    file_id = file_info["id"]
    print(f"Uploaded file: {file_id}")
    wait_for_file(file_id, api_key)
    if is_temp_dataset:
        upload_dataset.unlink(missing_ok=True)

    print("Creating eval")
    eval_obj = create_eval(api_key, args.name, grader_source)
    eval_id = eval_obj["id"]
    print(f"Created eval: {eval_id}")

    print(f"Creating run with model: {args.model}")
    run = create_run(api_key, eval_id, file_id, args.model, f"{args.name} / {args.model}")
    print(json.dumps({
        "eval_id": eval_id,
        "run_id": run.get("id"),
        "status": run.get("status"),
        "report_url": run.get("report_url"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
