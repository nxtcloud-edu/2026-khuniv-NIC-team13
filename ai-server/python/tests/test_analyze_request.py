import pytest
from pydantic import ValidationError

from app.schemas.analyze_request import AnalyzeRequestDto


def _valid_kwargs(**overrides):
    base = dict(
        userId="user-1",
        questionList=["question"],
        answerList=["answer"],
        applying_to="company",
        applying_as="position",
    )
    base.update(overrides)
    return base


def test_valid_request_passes():
    AnalyzeRequestDto(**_valid_kwargs())


def test_rejects_missing_user_id():
    with pytest.raises(ValidationError):
        AnalyzeRequestDto(**{k: v for k, v in _valid_kwargs().items() if k != "userId"})


def test_rejects_blank_user_id():
    with pytest.raises(ValidationError):
        AnalyzeRequestDto(**_valid_kwargs(userId="   "))


def test_rejects_empty_question_list():
    with pytest.raises(ValidationError):
        AnalyzeRequestDto(**_valid_kwargs(questionList=[]))


def test_rejects_empty_answer_list():
    with pytest.raises(ValidationError):
        AnalyzeRequestDto(**_valid_kwargs(answerList=[]))


def test_rejects_blank_question_element():
    with pytest.raises(ValidationError):
        AnalyzeRequestDto(**_valid_kwargs(questionList=["   "]))


def test_rejects_blank_answer_element():
    with pytest.raises(ValidationError):
        AnalyzeRequestDto(**_valid_kwargs(answerList=["   "]))


def test_rejects_missing_company():
    with pytest.raises(ValidationError):
        AnalyzeRequestDto(**{k: v for k, v in _valid_kwargs().items() if k != "applying_to"})


def test_rejects_missing_job_position():
    with pytest.raises(ValidationError):
        AnalyzeRequestDto(**{k: v for k, v in _valid_kwargs().items() if k != "applying_as"})


def test_rejects_question_answer_count_mismatch():
    with pytest.raises(ValidationError):
        AnalyzeRequestDto(**_valid_kwargs(answerList=["answer", "extra"]))


def test_accepts_legacy_applying_field_aliases():
    request = AnalyzeRequestDto.model_validate(
        {
            "userId": "user-1",
            "questionList": ["question"],
            "answerList": ["answer"],
            "applying_to": "company",
            "applying_as": "position",
        }
    )

    assert request.company == "company"
    assert request.job_position == "position"


def test_accepts_camel_case_company_and_job_position_field_names():
    request = AnalyzeRequestDto.model_validate(
        {
            "userId": "user-1",
            "questionList": ["question"],
            "answerList": ["answer"],
            "company": "company",
            "jobPosition": "position",
        }
    )

    assert request.company == "company"
    assert request.job_position == "position"
