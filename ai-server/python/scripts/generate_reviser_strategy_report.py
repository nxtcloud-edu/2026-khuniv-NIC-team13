#!/usr/bin/env python3
"""Build Markdown and PDF reports for the measured EXAONE Reviser comparison."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path
from statistics import mean, median

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


SCRIPT_DIR = Path(__file__).resolve().parent
BASELINE_PATH = SCRIPT_DIR / "upstage_compare_score_reviser_4096_result.json"
SAMPLED_FIVE_PATH = SCRIPT_DIR / "reviser_strategy_revision_5runs.json"
HYBRID_FIVE_PATH = SCRIPT_DIR / "reviser_strategy_revision_hybrid_5runs.json"
SEVEN_PATH = SCRIPT_DIR / "reviser_strategy_revision_7attempts_7runs.json"
MARKDOWN_PATH = SCRIPT_DIR / "reviser_strategy_revision_report.md"
PDF_PATH = SCRIPT_DIR / "reviser_strategy_revision_report.pdf"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * ratio
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def measured_row(name: str, data: dict) -> dict:
    results = data["results"]
    times = [float(result["elapsed_seconds"]) for result in results]
    repairs = sum(int(result["targeted_repairs"]) for result in results)
    fallbacks = sum(int(result["safe_fallbacks"]) for result in results)
    total_answers = sum(len(result["answer_similarities"]) for result in results)
    revised = sum(
        similarity <= 0.92
        for result in results
        for similarity in result["answer_similarities"]
    )
    calls = sum(3 + int(result["targeted_repairs"]) for result in results)
    return {
        "name": name,
        "runs": len(results),
        "revised": revised,
        "total_answers": total_answers,
        "revised_rate": revised / total_answers * 100,
        "fallbacks": fallbacks,
        "repairs": repairs,
        "calls": calls,
        "calls_mean": calls / len(results),
        "mean": mean(times),
        "median": median(times),
        "p95": percentile(times, 0.95),
        "minimum": min(times),
        "maximum": max(times),
    }


def baseline_row(data: dict) -> dict:
    original = data["request"]["answerList"]
    revised = data["revise_result"]["best_reply"]
    changed = sum(left.strip() != right.strip() for left, right in zip(original, revised))
    return {
        "name": "변경 전 저장 결과",
        "runs": 1,
        "revised": changed,
        "total_answers": len(original),
        "revised_rate": changed / len(original) * 100,
        "fallbacks": data["fallbacks"].count("revise_safe_fallback"),
        "repairs": data["fallbacks"].count("revise_targeted_repair"),
        "calls": None,
        "calls_mean": None,
        "mean": float(data["node_seconds"]["REVISE"]),
        "median": float(data["node_seconds"]["REVISE"]),
        "p95": float(data["node_seconds"]["REVISE"]),
        "minimum": float(data["node_seconds"]["REVISE"]),
        "maximum": float(data["node_seconds"]["REVISE"]),
    }


def format_row(row: dict) -> list[str]:
    calls = "-" if row["calls_mean"] is None else f'{row["calls_mean"]:.2f}'
    return [
        row["name"],
        str(row["runs"]),
        f'{row["revised"]}/{row["total_answers"]} ({row["revised_rate"]:.1f}%)',
        str(row["fallbacks"]),
        str(row["repairs"]),
        calls,
        f'{row["mean"]:.3f}s',
        f'{row["p95"]:.3f}s',
        f'{row["maximum"]:.3f}s',
    ]


def build_markdown(rows: list[dict], final: dict, baseline: dict) -> str:
    final_row = rows[-1]
    five_row = rows[-2]
    representative = final["results"][2]
    original = baseline["request"]["answerList"]
    revised = representative["best_reply"]
    similarities = representative["answer_similarities"]
    latency_delta = (final_row["mean"] / five_row["mean"] - 1) * 100
    tail_delta = (final_row["p95"] / five_row["p95"] - 1) * 100

    lines = [
        "# EXAONE 자기소개서 Reviser 수정률·Latency 비교 보고서",
        "",
        "- 입력: `scripts/upstage_compare_score_reviser_4096_result.json`에 저장된 동일 3문항",
        "- 모델: `LGAI-EXAONE/K-EXAONE-236B-A23B` (Friendli OpenAI-compatible API)",
        "- 운영 확정 설정: 첫 생성 `thinking=false, temperature=0`, 교정 생성 `thinking=false, temperature=1.0, top_p=0.95`, 문항별 최대 5회, 호출당 최대 4,096토큰",
        "- 실제 수정 판정: 원문과 불일치하고 100자 이상 답변의 SequenceMatcher 유사도가 0.92 이하이며 모든 코드 검증을 통과한 경우",
        "",
        "## 결론",
        "",
        f'- 변경 전 저장 결과는 3문항 모두 원문과 완전히 같았습니다. 비교용 7회 한도 실측에서는 {final_row["revised"]}/{final_row["total_answers"]}개({final_row["revised_rate"]:.1f}%)가 실제 수정됐습니다.',
        f'- 5회 한도 대비 수정률은 {five_row["revised_rate"]:.1f}% → {final_row["revised_rate"]:.1f}%, 평균 latency는 {five_row["mean"]:.3f}초 → {final_row["mean"]:.3f}초({latency_delta:+.1f}%)였습니다.',
        f'- 7회 한도 p95는 {final_row["p95"]:.3f}초로 5회 한도보다 {tail_delta:+.1f}% 증가했고, 동일한 `6개월간` 오류가 반복된 실행은 최대 {final_row["maximum"]:.3f}초 후에도 원문 fallback됐습니다.',
        "- 결론적으로 7회는 수정률을 소폭 높였지만 반복 불가능한 오류를 해결하지 못하며 꼬리 지연을 키웁니다.",
        "",
        "## 실측 비교",
        "",
        "| 설정 | 실행 | 실제 수정 | 원문 fallback | 교정 호출 | 평균 후보 호출/실행 | 평균 | p95 | 최대 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        values = format_row(row)
        lines.append("| " + " | ".join(values) + " |")

    lines.extend(
        [
            "",
            "## 현재 LLM에 전달되는 수정 정보",
            "",
            "- Evaluate의 전략명을 원문 안전 편집 동작으로 변환한 `editing_plan`",
            "- 결론 우선 배치, 인과관계 연결, 문장 순서 재구성, 수치·성과 배치, 직무 연결 중 적용 가능한 작업",
            "- 문항별 질문·원문, 목표 글자 수, 반드시 보존할 숫자와 영문 기술명",
            "- 원문에 없어 사용하면 안 되는 행동·기술 표현",
            "- 재시도 시 직전 후보와 알고리즘이 검출한 `problems_to_fix`",
            "",
            "재시도 여부는 LLM이 아니라 Python 검증기가 결정합니다. LLM은 수정 후보만 생성하고, 코드가 동일/근접 복사·숫자 누락·새 사실·깨진 문자·문장 파편·중복·분량을 검사합니다.",
            "",
            "## 정성 품질 감사",
            "",
            "코드 검증 기준으로는 19/21개가 수정됐지만, 사람이 결과를 다시 읽었을 때 최소 5개 답변에서 의미 귀속 위험을 확인했습니다.",
            "",
            "| 실행/문항 | 관찰 | 위험 |",
            "|---|---|---|",
            "| 2/2 | `6개월간 인턴십`을 `6개월간 지속된 문제 해결 과정`으로 연결 | 기간의 대상 변경 |",
            "| 5/2, 6/2, 7/2 | 원문에 없는 `삼성전자 백엔드 인턴십`으로 표현 | 회사 정보가 지원자 경력에 잘못 귀속 |",
            "| 7/1 | 원문의 `DS부문이 다루는`을 `DS부문이 주도하는`으로 강화 | 회사 사실 강도 상승 |",
            "",
            "따라서 90.5%는 구조적 수정률이며 최종 제출 품질 통과율로 해석하면 안 됩니다. 위에서 식별한 5건을 제외한 보수적 수동 검토 통과 하한은 16/21(76.2%)입니다.",
            "",
            "## 대표 결과 — 운영 5회 설정 실행 3",
            "",
        ]
    )
    for index, (source, output, similarity) in enumerate(
        zip(original, revised, similarities), start=1
    ):
        lines.extend(
            [
                f"### 문항 {index} — 유사도 {similarity:.4f}",
                "",
                f"원문: {source}",
                "",
                f"수정: {output}",
                "",
            ]
        )

    lines.extend(
        [
            "## 권고",
            "",
            "- 5회·7회 실측 비교 후 운영 기본값은 문항별 최대 5회로 확정해 코드에 반영했습니다.",
            "- 운영 적용 범위를 넓히기 전, 숫자 수식 대상과 회사/지원자 사실 귀속을 문장 단위로 검증하는 보완이 우선입니다.",
            "- 동일 오류 재시도는 2~3회 이후 효율이 급격히 낮으므로 오류 유형별 결정적 복원 또는 더 좁은 필드 교정이 latency 개선에 유리합니다.",
            "- 표본이 5회와 7회로 작고 EXAONE 샘플링 변동이 있으므로 수정률 차이를 통계적으로 확정하지 않습니다.",
            "",
            "## 원시 측정 파일",
            "",
            "- `scripts/reviser_strategy_revision_5runs.json` — 샘플링-only 5회 한도 중간 실험",
            "- `scripts/reviser_strategy_revision_hybrid_5runs.json` — 유지된 하이브리드 5회 한도 실험",
            "- `scripts/reviser_strategy_revision_final_5runs.json` — 폐기한 숫자 문맥/최적 후보 실험",
            "- `scripts/reviser_strategy_revision_7attempts_7runs.json` — 비교용 7회 한도/7회 반복 실험",
            "",
        ]
    )
    return "\n".join(lines)


def register_fonts() -> None:
    font_dir = SCRIPT_DIR / "fonts"
    pdfmetrics.registerFont(TTFont("NotoKR", str(font_dir / "NotoSansKR-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("NotoKR-Bold", str(font_dir / "NotoSansKR-Bold.ttf")))


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def build_pdf(rows: list[dict], final: dict, baseline: dict) -> None:
    register_fonts()
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("title", parent=base["Title"], fontName="NotoKR-Bold", fontSize=18, leading=24, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="NotoKR-Bold", fontSize=13, leading=18, textColor=colors.HexColor("#1a3a5c"), spaceBefore=12, spaceAfter=7),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontName="NotoKR-Bold", fontSize=10.5, leading=15, spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName="NotoKR", fontSize=9, leading=14, spaceAfter=5),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName="NotoKR", fontSize=7.4, leading=10),
        "small_bold": ParagraphStyle("small_bold", parent=base["BodyText"], fontName="NotoKR-Bold", fontSize=7.4, leading=10),
    }
    doc = SimpleDocTemplate(str(PDF_PATH), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    story = [
        p("EXAONE 자기소개서 Reviser 수정률·Latency 비교 보고서", styles["title"]),
        p("동일 3문항 · 실제 Friendli EXAONE 호출 · 2026-08-13", styles["body"]),
        p("핵심 결과", styles["h2"]),
        p("변경 전 저장 결과는 3문항 모두 원문과 같았습니다. 비교용 7회 한도 실측은 21개 중 19개(90.5%)가 구조적 수정 판정을 통과했고, 원문 fallback은 2개였습니다.", styles["body"]),
        p("평균 latency 25.437초, 중앙값 22.450초, p95 38.755초, 최대 42.859초입니다. 일곱 번의 교정도 동일한 6개월간 오류를 해결하지 못한 사례가 있어 꼬리 지연 위험이 남습니다.", styles["body"]),
        p("실측 비교", styles["h2"]),
    ]
    header = [p(value, styles["small_bold"]) for value in ["설정", "실행", "수정", "fallback", "교정", "호출/실행", "평균", "p95", "최대"]]
    table_data = [header] + [[p(value, styles["small"]) for value in format_row(row)] for row in rows]
    table = Table(table_data, colWidths=[35 * mm, 11 * mm, 22 * mm, 14 * mm, 13 * mm, 17 * mm, 16 * mm, 16 * mm, 16 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#b8c2cc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#eaf2f8")),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([table, Spacer(1, 6), p("수정 여부와 재시도는 LLM이 아니라 Python 검증기가 결정합니다. LLM에는 Evaluate 전략을 안전한 editing_plan으로 변환해 전달하며, 재시도에는 직전 후보와 검출된 오류를 제공합니다.", styles["body"]), p("정성 품질 감사", styles["h2"]), p("구조적 수정 19개 중 최소 5개에서 의미 귀속 위험을 확인했습니다: 6개월이라는 기간의 대상 변경 1건, 삼성전자를 인턴십 회사로 잘못 귀속한 답변 3건, 회사가 다루는 영역을 주도한다고 강화한 답변 1건입니다. 보수적 수동 검토 통과 하한은 16/21(76.2%)입니다.", styles["body"]), p("따라서 90.5%는 최종 제출 품질 통과율이 아니라 문자열 변화·형식·기본 사실 검증을 통과한 구조적 수정률입니다.", styles["body"]), p("운영 결정", styles["h2"]), p("5회·7회 실측 비교 후 현재 코드는 문항별 최대 5회로 확정했습니다. 7회는 수정률을 소폭 높였지만 동일 오류 반복 시 p95와 최대 latency가 크게 증가했습니다. 숫자의 수식 대상과 회사/지원자 사실 귀속을 문장 단위로 검증하는 보완은 별도 후속 과제입니다.", styles["body"]), PageBreak(), p("대표 결과 — 운영 5회 설정 실행 3", styles["h2"])])
    representative = final["results"][2]
    for index, (source, output, similarity) in enumerate(zip(baseline["request"]["answerList"], representative["best_reply"], representative["answer_similarities"]), start=1):
        story.extend([p(f"문항 {index} · 유사도 {similarity:.4f}", styles["h3"]), p("원문", styles["small_bold"]), p(source, styles["body"]), p("수정", styles["small_bold"]), p(output, styles["body"]), Spacer(1, 4)])
    doc.build(story)


def main() -> None:
    baseline = load(BASELINE_PATH)
    sampled_five = load(SAMPLED_FIVE_PATH)
    hybrid_five = load(HYBRID_FIVE_PATH)
    seven = load(SEVEN_PATH)
    rows = [
        baseline_row(baseline),
        measured_row("샘플링-only · 최대 5회", sampled_five),
        measured_row("하이브리드 · 최대 5회", hybrid_five),
        measured_row("하이브리드 · 최대 7회", seven),
    ]
    MARKDOWN_PATH.write_text(build_markdown(rows, hybrid_five, baseline) + "\n", encoding="utf-8")
    build_pdf(rows, hybrid_five, baseline)
    print(f"Saved: {MARKDOWN_PATH}")
    print(f"Saved: {PDF_PATH}")


if __name__ == "__main__":
    main()
