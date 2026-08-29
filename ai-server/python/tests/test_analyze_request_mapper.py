from app.mappers.analyze_request_mapper import to_agent_state
from app.schemas.analyze_request import AnalyzeRequestDto


def test_to_agent_state_maps_all_analyze_request_fields():
    request = AnalyzeRequestDto.model_validate(
        {
            "userId": "user-1",
            "questionList": ["지원 동기", "성장 과정"],
            "answerList": ["지원 동기 답변", "성장 과정 답변"],
            "education": "학사",
            "gpa": 4.1,
            "major": "컴퓨터공학",
            "backgroundCareerAward": "인턴 및 공모전 수상",
            "linguisticAbility": "TOEIC 900",
            "certificates": "정보처리기사",
            "company": "Pertineo",
            "jobPosition": "Backend Engineer",
            "jobField": "engineering",
            "division": "AI Platform",
            "applyUrl": "https://example.com/jobs/1",
        }
    )

    state = to_agent_state(request)

    assert state.user_id == request.user_id
    assert state.question_list == request.question_list
    assert state.answer_list == request.answer_list
    assert state.education == request.education
    assert state.gpa == request.gpa
    assert state.major == request.major
    assert state.background_career_award == request.background_career_award
    assert state.linguistic_ability == request.linguistic_ability
    assert state.certificates == request.certificates
    assert state.company == request.company
    assert state.job_position == request.job_position
    assert state.job_field == request.job_field
    assert state.division == request.division
    assert state.apply_url == request.apply_url
