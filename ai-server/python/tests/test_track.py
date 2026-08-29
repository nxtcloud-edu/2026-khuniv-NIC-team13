import pytest

from app.workflow.track import Track


def test_parse_accepts_trimmed_case_insensitive_business():
    assert Track.parse(" business ") == Track.BUSINESS
    assert Track.parse("BUSINESS") == Track.BUSINESS
    assert Track.parse("BuSiNeSs") == Track.BUSINESS


def test_parse_accepts_trimmed_case_insensitive_engineering():
    assert Track.parse(" engineering ") == Track.ENGINEERING
    assert Track.parse("ENGINEERING") == Track.ENGINEERING
    assert Track.parse("EnGiNeErInG") == Track.ENGINEERING


def test_parse_accepts_sentence_when_exactly_one_track_token_exists():
    assert Track.parse("The applicant belongs to the business track.") == Track.BUSINESS
    assert Track.parse("Classified as engineering track.") == Track.ENGINEERING


def test_parse_rejects_blank_unknown_and_ambiguous_sentence():
    with pytest.raises(ValueError):
        Track.parse(None)
    with pytest.raises(ValueError):
        Track.parse(" ")
    with pytest.raises(ValueError):
        Track.parse("design")
    with pytest.raises(ValueError):
        Track.parse("business or engineering")


def test_persistence_value_returns_repository_value():
    assert Track.BUSINESS.persistence_value() == "business"
    assert Track.ENGINEERING.persistence_value() == "engineering"
