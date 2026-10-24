"""Platform indicators aggregation.

The calculation rules are documented in docs/INDICATORS.md and must be kept in
sync with this module.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import ColumnElement, Select, exists, func, or_, select
from sqlalchemy.orm import QueryableAttribute, Session

from app.core.errors import ProblemException
from app.db.models.app_user import AppUser
from app.db.models.application import Application
from app.db.models.candidate import Candidate
from app.db.models.company import Company
from app.db.models.enums import ApplicationStatus
from app.db.models.job import Job
from app.db.models.resume import Resume
from app.indicators.schemas.indicator_filters import IndicatorFilters
from app.indicators.schemas.platform_indicators import (
    AppliedFilters,
    IndicatorSegments,
    IndicatorTotals,
    PlatformIndicators,
)

COMPLETE_RESUME_PERCENTAGE = 100


@dataclass(frozen=True)
class _Period:
    """Half-open UTC interval: start is inclusive, end is exclusive."""

    start: datetime | None
    end: datetime | None


def get_platform_indicators(
    session: Session, filters: IndicatorFilters
) -> PlatformIndicators:
    _ensure_valid_period(filters)
    period = _period_of(filters)
    return PlatformIndicators(
        filters=_applied(filters),
        totals=IndicatorTotals(
            candidates=_count(session, _candidates(filters, period)),
            companies=_count(session, _companies(filters, period)),
            jobs=_count(session, _jobs(filters, period)),
            applications=_count(session, _applications(filters, period)),
            matches=_count(session, _matches(filters, period)),
        ),
        segments=IndicatorSegments(
            candidates_without_placement=_count(
                session, _candidates_without_placement(filters, period)
            ),
            incomplete_resumes=_count(session, _incomplete_resumes(filters, period)),
        ),
    )


def _ensure_valid_period(filters: IndicatorFilters) -> None:
    if filters.start_date is None or filters.end_date is None:
        return
    if filters.start_date <= filters.end_date:
        return
    raise ProblemException(
        status_code=422,
        title="Unprocessable Entity",
        code="invalid_period",
        detail="start_date must not be after end_date.",
    )


def _period_of(filters: IndicatorFilters) -> _Period:
    return _Period(start=_start_of(filters.start_date), end=_end_of(filters.end_date))


def _start_of(day: date | None) -> datetime | None:
    if day is None:
        return None
    return datetime.combine(day, time.min, tzinfo=UTC)


def _end_of(day: date | None) -> datetime | None:
    if day is None:
        return None
    return _start_of(day + timedelta(days=1))


def _applied(filters: IndicatorFilters) -> AppliedFilters:
    return AppliedFilters(
        start_date=filters.start_date,
        end_date=filters.end_date,
        candidate_availability=filters.candidate_availability,
        company_status=filters.company_status,
        job_status=filters.job_status,
        application_status=filters.application_status,
    )


def _count(session: Session, statement: Select[tuple[int]]) -> int:
    return session.scalar(statement) or 0


def _within(
    column: QueryableAttribute[datetime], period: _Period
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if period.start is not None:
        conditions.append(column >= period.start)
    if period.end is not None:
        conditions.append(column < period.end)
    return conditions


def _candidates(filters: IndicatorFilters, period: _Period) -> Select[tuple[int]]:
    conditions = _within(AppUser.created_at, period)
    if filters.candidate_availability is not None:
        conditions.append(Candidate.availability == filters.candidate_availability)
    return (
        select(func.count())
        .select_from(Candidate)
        .join(AppUser, AppUser.id == Candidate.id)
        .where(*conditions)
    )


def _companies(filters: IndicatorFilters, period: _Period) -> Select[tuple[int]]:
    conditions = _within(AppUser.created_at, period)
    if filters.company_status is not None:
        conditions.append(Company.status == filters.company_status)
    return (
        select(func.count())
        .select_from(Company)
        .join(AppUser, AppUser.id == Company.id)
        .where(*conditions)
    )


def _jobs(filters: IndicatorFilters, period: _Period) -> Select[tuple[int]]:
    conditions = _within(Job.created_at, period)
    if filters.job_status is not None:
        conditions.append(Job.status == filters.job_status)
    return select(func.count()).select_from(Job).where(*conditions)


def _applications(filters: IndicatorFilters, period: _Period) -> Select[tuple[int]]:
    conditions = _within(Application.created_at, period)
    if filters.application_status is not None:
        conditions.append(Application.status == filters.application_status)
    return select(func.count()).select_from(Application).where(*conditions)


def _matches(filters: IndicatorFilters, period: _Period) -> Select[tuple[int]]:
    return _applications(filters, period).where(Application.match_score.is_not(None))


def _candidates_without_placement(
    filters: IndicatorFilters, period: _Period
) -> Select[tuple[int]]:
    hired = exists().where(
        Application.candidate_id == Candidate.id,
        Application.status == ApplicationStatus.HIRED,
    )
    return _candidates(filters, period).where(~hired)


def _incomplete_resumes(
    filters: IndicatorFilters, period: _Period
) -> Select[tuple[int]]:
    return (
        _candidates(filters, period)
        .outerjoin(Resume, Resume.candidate_id == Candidate.id)
        .where(
            or_(
                Resume.id.is_(None),
                Resume.completion_percentage < COMPLETE_RESUME_PERCENTAGE,
            )
        )
    )
