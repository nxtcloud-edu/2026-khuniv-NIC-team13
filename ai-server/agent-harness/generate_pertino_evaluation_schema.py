from __future__ import annotations

import csv
import json
import re
import statistics
from pathlib import Path

from docx import Document
from pypdf import PdfReader


SOURCE_ROOT = Path(r"D:\잡파일\페르티네오 검증")
OUT_DIR = Path("docs")
QUALITY_MAP = {
    "상": "high_quality",
    "중": "average_quality",
    "하": "low_quality",
}

TARGET_OVERRIDES = {
    "X4.2Y4.0Z4.6 KAI 자소서.docx": {
        "company": "KAI",
        "position": "임무SW",
        "track": "engineering",
    },
    "X4.3Y4.5Z4.1 S&S TECH 자소서.docx": {
        "company": "에스엔에스텍",
        "position": "EUV 소재 및 나노박막 공정 개발",
        "track": "engineering",
    },
    "X4.3Y4.6Z4.5 AMAT 인턴 지원서.docx": {
        "company": "Applied Materials Korea",
        "position": "반도체 장비 엔지니어 인턴",
        "track": "engineering",
    },
    "X4.4Y4.6Z4.3 전략기획 자소서.pdf": {
        "company": "",
        "position": "전략기획 / 비즈니스 분석",
        "track": "business",
    },
    "X4.5Y4.4Z4.3 현대자소서.pdf": {
        "company": "현대자동차",
        "position": "대외협력",
        "track": "business",
    },
    "X4.5Y4.7Z4.6  한화시스템 자소서.txt": {
        "company": "한화시스템",
        "position": "시스템 엔지니어링",
        "track": "engineering",
    },
    "X3.7Y3.8Z3.6 항공엔진 직무 자소서.pdf": {
        "company": "한화에어로스페이스",
        "position": "항공엔진",
        "track": "engineering",
    },
    "X3.8 Y3.95 X3.7 현대면세점_영업관리.docx": {
        "company": "현대면세점",
        "position": "영업관리",
        "track": "business",
    },
    "X3.8Y3.9Z3.7 삼성물산 패션부문 자소서.docx": {
        "company": "삼성물산 패션부문",
        "position": "패션",
        "track": "business",
    },
    "X3.8Y3.9Z3.8 포스토 마케팅 자소서.docx": {
        "company": "포스코",
        "position": "마케팅",
        "track": "business",
    },
    "X3.8Y4.0X3.7 기아 자소서.docx": {
        "company": "기아",
        "position": "자동화 설비 기술 / 생산기술",
        "track": "engineering",
    },
    "X3.6Y3.1Z3.0 sk하이닉스 자소서.pdf": {
        "company": "SK하이닉스",
        "position": "제조/양산기술(P&T)",
        "track": "engineering",
    },
    "X3.6Y3.9Z3.5 대한항공 지원서.pdf": {
        "company": "대한항공",
        "position": "객실승무원",
        "track": "business",
    },
    "X4.0Y3.1Z3.1 삼성자소서.hwp": {
        "company": "삼성",
        "position": "",
        "track": "",
    },
}


def parse_scores(stem: str) -> tuple[float | None, float | None, float | None, str]:
    matches = list(re.finditer(r"([XYZ])\s*([0-5](?:\.\d+)?)", stem, flags=re.I))
    values = {"X": [], "Y": [], "Z": []}
    for match in matches:
        values[match.group(1).upper()].append(float(match.group(2)))

    notes: list[str] = []
    x = values["X"][0] if values["X"] else None
    y = values["Y"][0] if values["Y"] else None
    z = values["Z"][0] if values["Z"] else None

    if len(values["X"]) > 1:
        notes.append("duplicate_X")
    if z is None and len(values["X"]) > 1:
        z = values["X"][-1]
        notes.append("inferred_Z_from_repeated_X")

    return x, y, z, ";".join(notes)


def label_text(stem: str) -> str:
    text = re.sub(r"([XYZ])\s*[0-5](?:\.\d+)?", "", stem, flags=re.I).strip()
    return re.sub(r"\s+", " ", text)


def extract_text_metadata(path: Path) -> tuple[str, int, str]:
    ext = path.suffix.lower()
    if ext == ".hwp":
        return "unsupported", 0, "HWP extraction is unsupported in the current local environment."

    try:
        if ext == ".docx":
            text = "\n".join(paragraph.text for paragraph in Document(str(path)).paragraphs)
        elif ext == ".pdf":
            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext == ".txt":
            text = path.read_text(encoding="utf-8", errors="replace")
        else:
            return "unsupported", 0, f"Unsupported extension: {ext}"
    except Exception as exc:  # noqa: BLE001 - data extraction should preserve error detail.
        return "error", 0, f"{type(exc).__name__}: {str(exc)[:120]}"

    compact = re.sub(r"\s+", " ", text).strip()
    return "ok", len(compact), ""


def build_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    per_tier_counts = {tier: 0 for tier in QUALITY_MAP}

    for tier in ["상", "중", "하"]:
        for path in sorted((SOURCE_ROOT / tier).iterdir(), key=lambda item: item.name):
            if not path.is_file():
                continue

            per_tier_counts[tier] += 1
            x, y, z, score_note = parse_scores(path.stem)
            overall = round((x + y + z) / 3, 3) if None not in (x, y, z) else ""
            extraction_status, text_chars, extraction_note = extract_text_metadata(path)
            target = TARGET_OVERRIDES.get(path.name, {"company": "", "position": "", "track": ""})

            rows.append(
                {
                    "id": f"{QUALITY_MAP[tier]}-{per_tier_counts[tier]:03d}",
                    "tier": tier,
                    "quality_label": QUALITY_MAP[tier],
                    "file_name": path.name,
                    "file_type": path.suffix.lower().lstrip("."),
                    "source_path": str(path),
                    "label_text": label_text(path.stem),
                    "expected_x": x,
                    "expected_y": y,
                    "expected_z": z,
                    "expected_overall": overall,
                    "score_parse_note": score_note,
                    "text_extraction_status": extraction_status,
                    "text_chars": text_chars,
                    "text_extraction_note": extraction_note,
                    "needs_anonymization_review": "true",
                    "company": target["company"],
                    "position": target["position"],
                    "track": target["track"],
                    "expected_level": "",
                    "expected_reason": "",
                    "has_kpi": "",
                    "has_loop": "",
                    "has_reproducibility": "",
                    "role_level": "",
                    "domain_match": "",
                }
            )

    return rows


def write_manifest(rows: list[dict[str, object]]) -> None:
    fields = list(rows[0].keys())
    with (OUT_DIR / "pertino-evaluation-file-manifest.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_seed_json(rows: list[dict[str, object]]) -> None:
    cases = []
    for row in rows:
        cases.append(
            {
                "id": row["id"],
                "quality_label": row["quality_label"],
                "tier": row["tier"],
                "source": {
                    "path": row["source_path"],
                    "file_name": row["file_name"],
                    "file_type": row["file_type"],
                    "label_text": row["label_text"],
                },
                "target": {
                    "company": row["company"],
                    "position": row["position"],
                    "job_field": "",
                    "division": "",
                    "track": row["track"],
                },
                "resume_text": "",
                "expected_scores": {
                    "x": row["expected_x"],
                    "y": row["expected_y"],
                    "z": row["expected_z"],
                    "overall": row["expected_overall"],
                    "level": row["expected_level"],
                    "score_parse_note": row["score_parse_note"],
                    "human_reason": row["expected_reason"],
                    "x_reason": "",
                    "y_reason": "",
                    "z_reason": "",
                },
                "rubric_flags": {
                    "has_kpi": None,
                    "has_loop": None,
                    "has_reproducibility": None,
                    "role_level": row["role_level"],
                    "domain_match": row["domain_match"],
                    "expected_caps": [],
                    "expected_gates": [],
                    "required_evidence": [],
                    "missing_evidence": [],
                    "forbidden_claims": [],
                },
                "text_extraction": {
                    "status": row["text_extraction_status"],
                    "chars": row["text_chars"],
                    "note": row["text_extraction_note"],
                },
                "privacy": {
                    "needs_anonymization_review": True,
                    "anonymized": False,
                    "pii_notes": "",
                },
                "notes": "",
            }
        )

    (OUT_DIR / "pertino-evaluation-dataset-seed.json").write_text(
        json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def write_summary(rows: list[dict[str, object]]) -> None:
    summary: dict[str, object] = {
        "source_root": str(SOURCE_ROOT),
        "total_files": len(rows),
        "by_tier": {},
        "notes": [
            "quality_label maps 상=high_quality, 중=average_quality, 하=low_quality.",
            "Rows with inferred_Z_from_repeated_X should be manually confirmed.",
            "HWP extraction is unsupported in the current local environment.",
            "Do not publish raw resume text before anonymization review.",
        ],
    }

    for tier in ["상", "중", "하"]:
        part = [row for row in rows if row["tier"] == tier]
        summary["by_tier"][tier] = {
            "count": len(part),
            "quality_label": QUALITY_MAP[tier],
            "avg_x": round(statistics.mean(float(row["expected_x"]) for row in part), 3),
            "avg_y": round(statistics.mean(float(row["expected_y"]) for row in part), 3),
            "avg_z": round(statistics.mean(float(row["expected_z"]) for row in part), 3),
            "avg_overall": round(statistics.mean(float(row["expected_overall"]) for row in part), 3),
            "min_overall": min(float(row["expected_overall"]) for row in part),
            "max_overall": max(float(row["expected_overall"]) for row in part),
        }

    (OUT_DIR / "pertino-evaluation-score-analysis.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def write_schema() -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://pertino.local/schemas/evaluation-case.schema.json",
        "title": "PertineoEvaluationCase",
        "type": "object",
        "required": ["id", "quality_label", "source", "expected_scores", "text_extraction", "privacy"],
        "properties": {
            "id": {"type": "string"},
            "quality_label": {
                "type": "string",
                "enum": [
                    "high_quality",
                    "average_quality",
                    "low_quality",
                    "short_or_insufficient",
                    "job_company_mismatch",
                    "kpi_without_loop",
                    "hallucination_trap",
                ],
            },
            "tier": {"type": "string", "enum": ["상", "중", "하"]},
            "source": {
                "type": "object",
                "required": ["path", "file_name", "file_type"],
                "properties": {
                    "path": {"type": "string"},
                    "file_name": {"type": "string"},
                    "file_type": {"type": "string"},
                    "label_text": {"type": "string"},
                },
            },
            "target": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "position": {"type": "string"},
                    "job_field": {"type": "string"},
                    "division": {"type": "string"},
                    "track": {"type": "string", "enum": ["", "business", "engineering"]},
                },
            },
            "resume_text": {
                "type": "string",
                "description": "Anonymized text only. Leave empty and use source.path until privacy review is complete.",
            },
            "expected_scores": {
                "type": "object",
                "required": ["x", "y", "z", "overall"],
                "properties": {
                    "x": {"type": "number", "minimum": 1, "maximum": 5},
                    "y": {"type": "number", "minimum": 1, "maximum": 5},
                    "z": {"type": "number", "minimum": 1, "maximum": 5},
                    "overall": {"type": "number", "minimum": 1, "maximum": 5},
                    "level": {
                        "type": "string",
                        "enum": ["", "매우 높음", "높음", "보통", "낮음", "매우 낮음"],
                    },
                    "score_parse_note": {"type": "string"},
                    "human_reason": {"type": "string"},
                    "x_reason": {"type": "string"},
                    "y_reason": {"type": "string"},
                    "z_reason": {"type": "string"},
                },
            },
            "rubric_flags": {
                "type": "object",
                "properties": {
                    "has_kpi": {"type": ["boolean", "null"]},
                    "has_loop": {"type": ["boolean", "null"]},
                    "has_reproducibility": {"type": ["boolean", "null"]},
                    "role_level": {
                        "type": "string",
                        "enum": ["", "none", "support", "participant", "partial_owner", "core_owner", "leader"],
                    },
                    "domain_match": {
                        "type": "string",
                        "enum": ["", "none", "weak", "partial", "strong", "excellent"],
                    },
                    "expected_caps": {"type": "array", "items": {"type": "string"}},
                    "expected_gates": {"type": "array", "items": {"type": "string"}},
                    "required_evidence": {"type": "array", "items": {"type": "string"}},
                    "missing_evidence": {"type": "array", "items": {"type": "string"}},
                    "forbidden_claims": {"type": "array", "items": {"type": "string"}},
                },
            },
            "text_extraction": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["ok", "unsupported", "error", "not_attempted"]},
                    "chars": {"type": "integer", "minimum": 0},
                    "note": {"type": "string"},
                },
            },
            "privacy": {
                "type": "object",
                "properties": {
                    "needs_anonymization_review": {"type": "boolean"},
                    "anonymized": {"type": "boolean"},
                    "pii_notes": {"type": "string"},
                },
            },
            "notes": {"type": "string"},
        },
    }
    (OUT_DIR / "pertino-evaluation-dataset-schema.json").write_text(
        json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    rows = build_rows()
    write_manifest(rows)
    write_seed_json(rows)
    write_summary(rows)
    write_schema()
    print(
        json.dumps(
            {
                "created": [
                "docs/pertino-evaluation-file-manifest.csv",
                "docs/pertino-evaluation-dataset-seed.json",
                "docs/pertino-evaluation-score-analysis.json",
                "docs/pertino-evaluation-dataset-schema.json",
                ],
                "rows": len(rows),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
