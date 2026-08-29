#!/usr/bin/env python3
"""Render a JSON analysis result (from run_analyze_to_json.py, or any JSON
with the same shape) into a formatted PDF evaluation report.

Uses reportlab only (pure Python, no system font/library dependencies) with
a bundled Korean TrueType font under scripts/fonts/, so it runs anywhere
without needing Homebrew/system packages.

Usage:
    python scripts/json_to_pdf_report.py
    python scripts/json_to_pdf_report.py --json scripts/analysis_result.json \
        --out scripts/analysis_report.pdf
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

SCRIPT_DIR = Path(__file__).resolve().parent
FONT_DIR = SCRIPT_DIR / "fonts"


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("NotoKR", str(FONT_DIR / "NotoSansKR-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("NotoKR-Bold", str(FONT_DIR / "NotoSansKR-Bold.ttf")))


def build_styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitleKR", parent=base["Title"], fontName="NotoKR-Bold", fontSize=19,
            leading=24, spaceAfter=4, textColor=colors.HexColor("#1a1a1a"),
        ),
        "subtitle": ParagraphStyle(
            "SubtitleKR", parent=base["Normal"], fontName="NotoKR", fontSize=10,
            leading=15, textColor=colors.HexColor("#666666"), spaceAfter=14,
        ),
        "h2": ParagraphStyle(
            "H2KR", parent=base["Heading2"], fontName="NotoKR-Bold", fontSize=13.5,
            leading=18, spaceBefore=16, spaceAfter=8, textColor=colors.HexColor("#1a3a5c"),
        ),
        "h3": ParagraphStyle(
            "H3KR", parent=base["Heading3"], fontName="NotoKR-Bold", fontSize=11.3,
            leading=15, spaceBefore=10, spaceAfter=5, textColor=colors.HexColor("#2c5b8a"),
        ),
        "body": ParagraphStyle(
            "BodyKR", parent=base["Normal"], fontName="NotoKR", fontSize=10, leading=15,
            spaceAfter=6,
        ),
        "bold_body": ParagraphStyle(
            "BoldBodyKR", parent=base["Normal"], fontName="NotoKR-Bold", fontSize=10, leading=15,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "BulletKR", parent=base["Normal"], fontName="NotoKR", fontSize=9.6, leading=14,
        ),
        "note": ParagraphStyle(
            "NoteKR", parent=base["Normal"], fontName="NotoKR", fontSize=8.8, leading=13,
            textColor=colors.HexColor("#666666"),
        ),
        "score": ParagraphStyle(
            "ScoreKR", parent=base["Normal"], fontName="NotoKR-Bold", fontSize=22, leading=26,
            textColor=colors.HexColor("#0b3d91"), alignment=1,
        ),
        "axis_label": ParagraphStyle(
            "AxisLabelKR", parent=base["Normal"], fontName="NotoKR-Bold", fontSize=11,
            leading=14, textColor=colors.white, alignment=1,
        ),
        "cell": ParagraphStyle(
            "CellKR", parent=base["Normal"], fontName="NotoKR", fontSize=8.8, leading=12.5,
        ),
        "cell_bold": ParagraphStyle(
            "CellBoldKR", parent=base["Normal"], fontName="NotoKR-Bold", fontSize=8.8, leading=12.5,
        ),
    }


def bullets(items: Optional[List[str]], style: ParagraphStyle) -> Optional[ListFlowable]:
    if not items:
        return None
    return ListFlowable(
        [ListItem(Paragraph(str(item), style), leftIndent=6) for item in items],
        bulletType="bullet",
        start="•",
        leftIndent=12,
        bulletFontName="NotoKR",
        bulletFontSize=9,
    )


AXIS_COLORS = {"x": "#2c5b8a", "y": "#1a7a5c", "z": "#8a4b2c"}
AXIS_TITLES = {"x": "X축", "y": "Y축", "z": "Z축"}


def _unexpected_output_letters(value: Any) -> List[str]:
    findings: List[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, str):
            for character in item:
                codepoint = ord(character)
                expected_letter = (
                    "A" <= character <= "Z"
                    or "a" <= character <= "z"
                    or 0x1100 <= codepoint <= 0x11FF
                    or 0x3130 <= codepoint <= 0x318F
                    or 0xAC00 <= codepoint <= 0xD7A3
                )
                if character == "\ufffd" or (
                    unicodedata.category(character).startswith("L")
                    and not expected_letter
                ):
                    finding = f"{character} (U+{codepoint:04X})"
                    if finding not in findings:
                        findings.append(finding)
        elif isinstance(item, dict):
            for nested in item.values():
                visit(nested)
        elif isinstance(item, list):
            for nested in item:
                visit(nested)

    visit(value)
    return findings


def normalize_input(data: Dict[str, Any], input_path: Path) -> Dict[str, Any]:
    """Convert a comparison-harness report into the regular PDF input shape."""
    if not data.get("fixed_context") or not isinstance(data.get("results"), list):
        normalized = dict(data)
        notes = list(data.get("report_notes") or [])
        vector_context = data.get("vector_context")
        if isinstance(vector_context, dict):
            notes.append(
                "벡터 컨텍스트 조회 상태: "
                f"{vector_context.get('status', '-')} "
                f"(선택 키 {vector_context.get('selected_key_count', 0)}개, "
                f"조회 문서 {vector_context.get('document_count', 0)}개)."
            )

        fallbacks = data.get("fallbacks") or []
        if "workflow_retrying" in fallbacks:
            notes.append(
                "EVALUATE 첫 시도가 실패해 전체 EVALUATE를 한 번 재실행한 뒤 복구했습니다."
            )
        if "revise_targeted_repair" in fallbacks:
            notes.append(
                "Reviser의 특정 문항이 품질 검증에 실패해 그 문항만 한 번 다시 생성했습니다."
            )
        if "revise_numeric_qualifier_restore" in fallbacks:
            notes.append(
                "Reviser가 누락한 원문의 숫자 한정 표현은 새 사실을 만들지 않고 원문대로 복원했습니다."
            )
        if "revise_explanation_fallback" in fallbacks:
            notes.append(
                "Reviser 본문은 보존하고 품질 검증을 통과하지 못한 설명 필드만 안전한 문장으로 대체했습니다."
            )
        if "revise_safe_fallback" in fallbacks:
            notes.append(
                "Reviser 검증을 통과하지 못한 문항은 새 내용을 만들지 않고 원문을 보존했습니다."
            )

        revised = data.get("revise_result") or {}
        revised_count = len(revised.get("best_reply") or [])
        if revised_count:
            notes.append(f"Reviser는 최종 수정 답변 {revised_count}개를 반환했습니다.")

        evaluation_letters = _unexpected_output_letters(data.get("evaluate_result"))
        revision_letters = _unexpected_output_letters(data.get("revise_result"))
        if evaluation_letters:
            notes.append(
                "품질 경고: 최종 EVALUATE 응답에 비정상 외국 문자가 남았습니다: "
                + ", ".join(evaluation_letters)
                + "."
            )
        notes.append(
            "최종 Reviser 응답의 비정상 외국 문자 검사 결과: "
            + (", ".join(revision_letters) if revision_letters else "감지 없음")
            + "."
        )
        notes.append(
            "문자·숫자·영문 토큰 검증 통과는 문법과 문장 완결성까지 보장하지 않으므로 "
            "아래 수정 답변을 함께 검토해야 합니다."
        )
        normalized["report_notes"] = notes
        return normalized

    successful = [
        result
        for result in data["results"]
        if len(result.get("stats", [])) == 4
        and all(stat.get("success") for stat in result["stats"])
    ]
    if not successful:
        raise ValueError("comparison report has no successful four-stage result")

    representative = successful[0]
    request_path = Path(data["request"])
    if not request_path.is_absolute() and not request_path.exists():
        request_path = SCRIPT_DIR.parent / request_path
    request = json.loads(request_path.read_text(encoding="utf-8"))

    outputs = representative["outputs"]
    evaluation = (
        outputs.get("axes", {})
        | outputs.get("fit", {})
        | outputs.get("improvement", {})
        | outputs.get("strategy", {})
    )
    aggregate = data.get("aggregates", {}).get(representative["provider"], {})
    completed = aggregate.get("completed_runs", len(data["results"]))
    successes = aggregate.get("all_stage_successes", len(successful))
    failures = aggregate.get("all_stage_failures", completed - successes)
    elapsed = aggregate.get("elapsed_seconds", {}).get("mean")
    corrupt_runs = aggregate.get("runs_with_corrupt_characters")
    risky_runs = aggregate.get("runs_with_risky_claims")
    canonical_outputs = {
        json.dumps(result["outputs"], ensure_ascii=False, sort_keys=True)
        for result in successful
    }

    notes = [
        f"동일한 sample_analyze_request.json과 고정 컨텍스트로 EXAONE EVALUATE를 {completed}회 실행했습니다.",
        f"네 단계 전체 성공 {successes}회, 실패 {failures}회로 기술적 성공률은 {successes / completed:.0%}입니다.",
        f"전체 EVALUATE 평균 응답 시간은 {elapsed:.3f}초입니다.",
        "이번 측정은 axes, fit, improvement, strategy만 실행했으며 Schemer, 검색, 벡터 조회, Reviser는 포함하지 않았습니다.",
        f"아래 본문은 {representative['run']}회차 성공 응답이며, 성공 응답 {successes}개의 내용 일치 여부는 {'동일' if len(canonical_outputs) == 1 else '상이'}합니다.",
        f"품질 경고: 비정상 외국 문자가 감지된 실행은 {corrupt_runs}/{completed}, 근거 부족 단정 진단이 발생한 실행은 {risky_runs}/{completed}입니다.",
        "모델 응답을 정제하거나 수정하지 않고 그대로 수록했습니다. Reviser 수정 답변은 이번 보고서에 없습니다.",
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "request": request,
        "failed": False,
        "schemer_result": None,
        "track": request.get("jobField") or "-",
        "pass_score": "고정 컨텍스트 실행: 합격자 벤치마크 데이터 없음",
        "evaluate_result": evaluation,
        "revise_result": None,
        "report_notes": notes,
        "source_report": str(input_path),
    }


def build_axis_block(axis_key: str, axis: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> List[Any]:
    color = colors.HexColor(AXIS_COLORS.get(axis_key, "#333333"))
    header_style = ParagraphStyle(
        f"AxisHeader{axis_key}", parent=styles["axis_label"],
    )

    score = axis.get("score")
    score_cell = Paragraph(f"{score:.1f}" if isinstance(score, (int, float)) else "-", styles["score"])

    info_flow: List[Any] = []
    if axis.get("summary"):
        info_flow.append(Paragraph(f"<b>요약:</b> {axis['summary']}", styles["body"]))
    if axis.get("compare_score"):
        info_flow.append(Paragraph(f"<b>비교:</b> {axis['compare_score']}", styles["body"]))
    if axis.get("criteria"):
        info_flow.append(Paragraph("<b>기준</b>", styles["bold_body"]))
        b = bullets(axis["criteria"], styles["bullet"])
        if b:
            info_flow.append(b)
    if axis.get("basis"):
        info_flow.append(Paragraph("<b>근거</b>", styles["bold_body"]))
        b = bullets(axis["basis"], styles["bullet"])
        if b:
            info_flow.append(b)

    row = Table(
        [[Paragraph(AXIS_TITLES.get(axis_key, axis_key.upper()), header_style)],
         [score_cell]],
        colWidths=[24 * mm],
    )
    row.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), color),
        ("BACKGROUND", (0, 1), (0, 1), colors.HexColor("#f4f6f8")),
        ("TOPPADDING", (0, 0), (0, 0), 6),
        ("BOTTOMPADDING", (0, 0), (0, 0), 6),
        ("TOPPADDING", (0, 1), (0, 1), 10),
        ("BOTTOMPADDING", (0, 1), (0, 1), 10),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#dddddd")),
    ]))

    outer = Table([[row, info_flow]], colWidths=[26 * mm, None])
    outer.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (1, 0), (1, 0), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [outer, Spacer(1, 10)]


def build_report(data: Dict[str, Any], out_path: Path) -> None:
    register_fonts()
    styles = build_styles()

    request = data.get("request") or {}
    company = request.get("company") or request.get("applying_to") or "-"
    job_position = request.get("jobPosition") or request.get("applying_as") or "-"
    user_id = request.get("userId") or "-"
    questions: List[str] = request.get("questionList") or []
    answers: List[str] = request.get("answerList") or []

    schemer = data.get("schemer_result")
    track = data.get("track") or "-"
    pass_score = data.get("pass_score")
    evaluate = data.get("evaluate_result") or {}
    revise = data.get("revise_result") or {}
    generated_at = data.get("generated_at", "")

    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        topMargin=20 * mm, bottomMargin=18 * mm, leftMargin=20 * mm, rightMargin=20 * mm,
    )
    story: List[Any] = []

    # --- Header ---
    story.append(Paragraph("Pertineo AI 자기소개서 평가 리포트", styles["title"]))
    story.append(Paragraph(
        f"지원자: {user_id} &nbsp;|&nbsp; 지원 회사: {company} &nbsp;|&nbsp; 지원 직무: {job_position} "
        f"&nbsp;|&nbsp; 트랙: {track} &nbsp;|&nbsp; 생성 시각: {generated_at}",
        styles["subtitle"],
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dddddd")))
    story.append(Spacer(1, 8))

    if data.get("failed"):
        story.append(Paragraph(
            "⚠ 이 결과는 워크플로우 실행 중 오류가 발생한 상태에서 생성되었습니다. "
            "아래 내용 중 일부가 비어 있을 수 있습니다.",
            ParagraphStyle("Warn", parent=styles["body"], textColor=colors.HexColor("#c0392b")),
        ))

    report_notes = data.get("report_notes") or []
    if report_notes:
        story.append(Paragraph("실행 범위 및 검증 메모", styles["h2"]))
        note_list = bullets(report_notes, styles["bullet"])
        if note_list:
            story.append(note_list)

    # --- Schemer / validity ---
    story.append(Paragraph("자기소개서 유효성 검사", styles["h2"]))
    if isinstance(schemer, dict):
        q_valid = "통과" if schemer.get("is_question_valid") else "실패"
        a_valid = "통과" if schemer.get("is_answer_valid") else "실패"
        story.append(Paragraph(f"질문 유효성: <b>{q_valid}</b> &nbsp;&nbsp; 답변 유효성: <b>{a_valid}</b>", styles["body"]))
        if schemer.get("validation_reason"):
            story.append(Paragraph(f"사유: {schemer['validation_reason']}", styles["body"]))
    else:
        story.append(Paragraph(
            "이번 보고서 생성 범위에서는 Schemer를 실행하지 않았습니다.",
            styles["note"],
        ))

    # --- Overview ---
    if evaluate:
        story.append(Paragraph("종합 평가", styles["h2"]))
        level = evaluate.get("level", "-")
        story.append(Paragraph(f"경쟁력 수준: <b>{level}</b>", styles["body"]))
        if evaluate.get("job_summary"):
            story.append(Paragraph(evaluate["job_summary"], styles["body"]))
        if evaluate.get("overall"):
            story.append(Paragraph(evaluate["overall"], styles["body"]))

        # --- Pass score benchmark ---
        story.append(Paragraph("합격자 벤치마크 비교", styles["h3"]))
        if isinstance(pass_score, dict):
            rows = [
                [Paragraph("항목", styles["cell_bold"]), Paragraph("X", styles["cell_bold"]),
                 Paragraph("Y", styles["cell_bold"]), Paragraph("Z", styles["cell_bold"]),
                 Paragraph("종합", styles["cell_bold"])],
                [Paragraph("합격자 평균", styles["cell"]),
                 Paragraph(str(pass_score.get("x", "-")), styles["cell"]),
                 Paragraph(str(pass_score.get("y", "-")), styles["cell"]),
                 Paragraph(str(pass_score.get("z", "-")), styles["cell"]),
                 Paragraph(str(pass_score.get("overall", "-")), styles["cell"])],
            ]
            t = Table(rows, colWidths=[40 * mm, 30 * mm, 30 * mm, 30 * mm, 30 * mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t)
            story.append(Spacer(1, 6))
        elif isinstance(pass_score, str):
            story.append(Paragraph(pass_score, styles["note"]))
        else:
            story.append(Paragraph("합격자 벤치마크 데이터 없음", styles["note"]))

        # --- 3-axis evaluation ---
        story.append(Paragraph("3축 평가", styles["h2"]))
        for axis_key in ("x", "y", "z"):
            axis = evaluate.get(axis_key)
            if isinstance(axis, dict):
                story.extend(build_axis_block(axis_key, axis, styles))

        # --- Fit assessment ---
        story.append(Paragraph("적합도 평가", styles["h2"]))
        for label, key in (("Role Fit", "role_fit"), ("Domain Fit", "domain_fit"),
                           ("Culture Fit", "culture_fit"), ("Skill Fit", "skill_fit")):
            if evaluate.get(key):
                story.append(Paragraph(f"<b>{label}</b>", styles["bold_body"]))
                story.append(Paragraph(evaluate[key], styles["body"]))

        # --- Strength / weakness / advice ---
        story.append(Paragraph("강점 · 약점 · 조언", styles["h2"]))
        for label, key in (("강점", "strength"), ("약점", "weakness"), ("조언", "advice")):
            items = evaluate.get(key)
            if items:
                story.append(Paragraph(f"<b>{label}</b>", styles["h3"]))
                b = bullets(items, styles["bullet"])
                if b:
                    story.append(b)

        if evaluate.get("compare_prob"):
            story.append(Paragraph("합격 가능성 비교", styles["h3"]))
            b = bullets(evaluate["compare_prob"], styles["bullet"])
            if b:
                story.append(b)

        if evaluate.get("score_summary"):
            story.append(Paragraph("점수 총평", styles["h3"]))
            b = bullets(evaluate["score_summary"], styles["bullet"])
            if b:
                story.append(b)

        # --- Improvement strategy ---
        if evaluate.get("improve_overall") or evaluate.get("improve_strategy") or evaluate.get("improve_expectation"):
            story.append(Paragraph("개선 전략", styles["h2"]))
            if evaluate.get("improve_overall"):
                b = bullets(evaluate["improve_overall"], styles["bullet"])
                if b:
                    story.append(b)
            for strategy in evaluate.get("improve_strategy") or []:
                name = strategy.get("strategy_name", "-")
                story.append(Paragraph(f"<b>· {name}</b>", styles["h3"]))
                b = bullets(strategy.get("action_items"), styles["bullet"])
                if b:
                    story.append(b)
            if evaluate.get("improve_expectation"):
                story.append(Paragraph("기대 효과", styles["h3"]))
                b = bullets(evaluate["improve_expectation"], styles["bullet"])
                if b:
                    story.append(b)
    else:
        story.append(Paragraph(
            "평가 결과(evaluate_result)가 없습니다 — 워크플로우가 evaluate 단계까지 도달하지 못했습니다.",
            styles["note"],
        ))

    # --- Revised answers, per question ---
    best_reply = revise.get("best_reply") or []
    reply_reason = revise.get("reply_reason") or []
    expectation = revise.get("expectation") or []

    if best_reply:
        story.append(Paragraph("수정 제안 답변", styles["h2"]))
        for i, question in enumerate(questions):
            story.append(Paragraph(f"Q{i + 1}. {question}", styles["h3"]))
            if i < len(answers):
                story.append(Paragraph("<b>원본 답변</b>", styles["bold_body"]))
                story.append(Paragraph(answers[i], styles["body"]))
            if i < len(best_reply):
                story.append(Paragraph("<b>수정 제안</b>", styles["bold_body"]))
                story.append(Paragraph(best_reply[i], styles["body"]))
            if i < len(reply_reason):
                story.append(Paragraph(f"<i>수정 이유:</i> {reply_reason[i]}", styles["note"]))
            if i < len(expectation):
                story.append(Paragraph(f"<i>기대 효과:</i> {expectation[i]}", styles["note"]))
            story.append(Spacer(1, 8))

    doc.build(story)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", default="scripts/analysis_result.json", type=Path)
    parser.add_argument("--out", default="scripts/analysis_report.pdf", type=Path)
    args = parser.parse_args(argv)

    if not args.json.exists():
        print(f"입력 JSON을 찾을 수 없습니다: {args.json}", file=sys.stderr)
        print("먼저 run_analyze_to_json.py를 실행해서 결과를 만들어주세요.", file=sys.stderr)
        return 1

    data = json.loads(args.json.read_text(encoding="utf-8"))
    data = normalize_input(data, args.json)
    build_report(data, args.out)
    print(f"Saved: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
