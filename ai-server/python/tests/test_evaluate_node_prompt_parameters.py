from app.workflow.nodes.evaluate_node import system_prompt_parameters
from app.config.resources import read_text
from app.util.template import render


def test_system_prompt_parameters_include_vector_context_without_changing_db_context():
    params = system_prompt_parameters(
        "eval-prompts",
        "백엔드",
        "삼성",
        "기존 DB 합격자 데이터",
        "웹 검색 데이터",
        "벡터 유사 문서 데이터",
    )

    assert params["eval_prompts"] == "eval-prompts"
    assert params["position"] == "백엔드"
    assert params["company"] == "삼성"
    assert params["pass_score"] == "기존 DB 합격자 데이터"
    assert params["web_search"] == "웹 검색 데이터"
    assert params["vector_context"] == "벡터 유사 문서 데이터"


def test_evaluate_prompt_includes_rubric_once_and_uses_snake_case_fields():
    rubric = read_text("3D_Eval_Prompt_v2.txt") + "\n\n" + read_text("track", "engineering.txt")
    params = system_prompt_parameters(
        rubric,
        "소프트웨어 개발",
        "삼성전자",
        "합격자 데이터 없음",
        "웹 검색 데이터 없음",
        "유사 문서 없음",
    )

    prompt = render(read_text("prompts", "evaluate", "system.txt"), **params)

    assert prompt.count("0. Pertineo 시스템") == 1
    assert len(prompt) < 25000
    assert "compare_score" in prompt
    assert "compareScore" not in prompt
    assert "applicant_info와 questions/answers에서 직접 확인되는 내용만" in prompt
    assert '"~은 입력에서 확인되지 않습니다"' in prompt
    assert "지원자의 경험이나 성과로 귀속하지 않고" in prompt
    assert 'compare_score는 코드에서 최종 계산하므로 항상 "코드 계산 예정"' in prompt
