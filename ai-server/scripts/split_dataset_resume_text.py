import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "docs" / "pertino-evaluation-dataset-flat.jsonl"


QUESTION_MARKER = re.compile(r"(?<!\d)(?<!\d\.)(\d{1,2})\.\s*(?!\d)(?=\S)")
ANSWER_START_PATTERNS = [
    re.compile(r"필수\s*0\s*/\s*[\d,]+"),
    re.compile(r"\(\s*\d{2,4}\s*자[^)]*\)"),
    re.compile(r"\(\s*도전한 이유[^)]*\)"),
]


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def find_answer_start(segment: str) -> int | None:
    prefix = segment[:500]
    starts = []
    for pattern in ANSWER_START_PATTERNS:
        starts.extend(match.end() for match in pattern.finditer(prefix))

    if starts:
        return max(starts)

    phrase_starts = []
    for phrase in ("기술해주세요.", "작성해 주세요.", "서술해 주세요.", "기술하시오"):
        index = prefix.rfind(phrase)
        if index >= 0:
            phrase_starts.append(index + len(phrase))
    if phrase_starts:
        return max(phrase_starts)

    bracket = segment.find("<")
    if 20 <= bracket <= 260:
        return bracket

    return None


def parse_numbered_segments(text: str) -> tuple[list[str], list[str]]:
    matches = list(QUESTION_MARKER.finditer(text))
    if not matches:
        return [], []

    questions = []
    answers = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        segment = text[start:end].strip()
        segment = QUESTION_MARKER.sub("", segment, count=1).strip()
        answer_start = find_answer_start(segment)
        if answer_start is None:
            continue

        question = compact(segment[:answer_start])
        answer = compact(segment[answer_start:])
        if len(question) >= 8 and len(answer) >= 40:
            questions.append(question)
            answers.append(answer)

    return questions, answers


def parse_single_prompt(text: str) -> tuple[list[str], list[str]]:
    answer_start = find_answer_start(text)
    if answer_start is None:
        return ["자기소개서 전체 평가"], [text]

    question = compact(text[:answer_start])
    answer = compact(text[answer_start:])
    if len(question) < 8 or len(answer) < 40:
        return ["자기소개서 전체 평가"], [text]
    return [question], [answer]


def split_resume_text(text: str) -> tuple[list[str], list[str]]:
    text = text.strip()
    questions, answers = parse_numbered_segments(text)
    if questions and len(questions) == len(answers):
        return questions, answers
    return parse_single_prompt(text)


def main() -> None:
    rows = []
    for line in DATASET.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        questions, answers = split_resume_text(row["resume_text"])
        row["questions"] = questions
        row["answers"] = answers
        rows.append(row)

    DATASET.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )

    summary = {
        "rows": len(rows),
        "split_rows": sum(1 for row in rows if len(row["questions"]) > 1),
        "fallback_rows": sum(1 for row in rows if row["questions"] == ["자기소개서 전체 평가"]),
        "question_counts": {row["id"]: len(row["questions"]) for row in rows},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
