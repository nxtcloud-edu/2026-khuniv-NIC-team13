"""Deterministic, auditable career-job ranking."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import List, Optional, Sequence

from app.career.models import ExtractedJob, VerifiedJobPage
from app.schemas.career import (
    CareerProfileDto,
    FitScoreBreakdown,
    JobRecommendation,
)

_TERM_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9+.#_-]*|[가-힣]{2,}")
_YEAR_REQUIREMENT = re.compile(r"(\d+(?:\.\d+)?)\s*년")
_DATE_PATTERN = re.compile(r"(20\d{2})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})")
_NON_EVIDENCE_TERMS = {
    "경험",
    "개발",
    "관련",
    "업무",
    "이해",
    "능력",
    "활용",
    "필수",
    "우대",
    "보유",
    "가능",
}


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def deadline_is_past(value: Optional[str]) -> bool:
    if not value:
        return False
    match = _DATE_PATTERN.search(value)
    if not match:
        return False
    try:
        deadline = date(*(int(part) for part in match.groups()))
    except ValueError:
        return False
    return deadline < date.today()


def company_matches(company: str, targets: Sequence[str]) -> bool:
    normalized_company = compact(company)
    return any(
        normalized_company in compact(target) or compact(target) in normalized_company
        for target in targets
        if compact(target)
    )


def ground_extraction(posting: ExtractedJob, page: VerifiedJobPage) -> ExtractedJob:
    if not posting.deadline:
        return posting
    source = f"{page.hit.content} {page.page_text}"
    normalized_deadline = compact(posting.deadline)
    normalized_source = compact(source)
    if normalized_deadline in normalized_source:
        return posting
    deadline_match = _DATE_PATTERN.search(posting.deadline)
    source_dates = {match.groups() for match in _DATE_PATTERN.finditer(source)}
    if deadline_match and deadline_match.groups() in source_dates:
        return posting
    return posting.model_copy(update={"deadline": None})


def rank_job(
    posting: ExtractedJob,
    page: VerifiedJobPage,
    profile: CareerProfileDto,
    target_roles: Sequence[str],
    locations: Sequence[str],
    checked_at: datetime,
) -> JobRecommendation:
    profile_text = _profile_text(profile)
    matched_required, missing_required = _match_requirements(
        posting.required_requirements, profile_text
    )
    matched_preferred, _ = _match_requirements(
        posting.preferred_requirements, profile_text
    )

    breakdown = FitScoreBreakdown(
        role=round(30 * _role_match(posting.title, target_roles)),
        required=round(
            35
            * (
                len(matched_required) / len(posting.required_requirements)
                if posting.required_requirements
                else 0.65
            )
        ),
        preferred=round(
            10
            * (
                len(matched_preferred) / len(posting.preferred_requirements)
                if posting.preferred_requirements
                else 0.5
            )
        ),
        experience=_experience_score(posting, profile),
        location=_location_score(posting.location, locations),
        verification=5,
    )
    fit_score = min(100, sum(breakdown.model_dump().values()))
    matched = list(dict.fromkeys([*matched_required, *matched_preferred]))
    reason_parts = [f"이력과 공고의 적합도를 {fit_score}점으로 계산했습니다."]
    if matched:
        reason_parts.append(f"확인된 일치 요건은 {', '.join(matched[:3])}입니다.")
    if missing_required:
        reason_parts.append(
            f"지원 전 확인하거나 보완할 필수요건은 {', '.join(missing_required[:3])}입니다."
        )

    return JobRecommendation(
        company=posting.company or "확인 필요",
        title=posting.title or page.hit.title,
        url=page.final_url,
        source_domain=page.source_domain,
        deadline=posting.deadline,
        location=posting.location,
        employment_type=posting.employment_type,
        experience_level=posting.experience_level,
        verification_status="verified_active",
        fit_score=fit_score,
        score_breakdown=breakdown,
        required_requirements=posting.required_requirements,
        preferred_requirements=posting.preferred_requirements,
        matched_requirements=matched,
        missing_requirements=missing_required,
        recommendation_reason=" ".join(reason_parts),
        checked_at=checked_at,
    )


def profile_matches_requirement(
    requirement: str, profile: CareerProfileDto
) -> bool:
    matched, _ = _match_requirements([requirement], _profile_text(profile))
    return bool(matched)


def _profile_text(profile: CareerProfileDto) -> str:
    values: List[str] = [
        profile.education or "",
        profile.major or "",
        profile.experience_summary or "",
        profile.resume_text or "",
        *profile.skills,
        *profile.projects,
        *profile.certificates,
        *profile.languages,
    ]
    return compact(" ".join(values))


def _match_requirements(
    requirements: Sequence[str], profile_text: str
) -> tuple[List[str], List[str]]:
    matched: List[str] = []
    missing: List[str] = []
    for requirement in requirements:
        tokens = [compact(token) for token in _TERM_TOKEN.findall(requirement)]
        meaningful = [
            token
            for token in tokens
            if len(token) >= 2 and token not in _NON_EVIDENCE_TERMS
        ]
        if meaningful and any(token in profile_text for token in meaningful):
            matched.append(requirement)
        else:
            missing.append(requirement)
    return matched, missing


def _role_match(title: str, target_roles: Sequence[str]) -> float:
    normalized_title = compact(title)
    best = 0.0
    title_tokens = {compact(token) for token in _TERM_TOKEN.findall(title)}
    for role in target_roles:
        normalized_role = compact(role)
        if normalized_role and normalized_role in normalized_title:
            return 1.0
        role_tokens = {compact(token) for token in _TERM_TOKEN.findall(role)}
        role_tokens.discard("")
        if role_tokens:
            best = max(best, len(role_tokens & title_tokens) / len(role_tokens))
    return best


def _experience_score(posting: ExtractedJob, profile: CareerProfileDto) -> int:
    text = " ".join([posting.experience_level or "", *posting.required_requirements])
    years = [float(value) for value in _YEAR_REQUIREMENT.findall(text)]
    if years:
        return 10 if profile.experience_years >= min(years) else 0
    if "신입" in text:
        return 10 if profile.experience_years < 3 else 7
    return 7


def _location_score(location: Optional[str], preferred: Sequence[str]) -> int:
    if not preferred:
        return 7
    if not location:
        return 3
    normalized = compact(location)
    return 10 if any(compact(value) in normalized for value in preferred) else 0
