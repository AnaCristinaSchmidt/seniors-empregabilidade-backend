from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import require_administrator
from app.core.problem_details import PROBLEM_RESPONSE
from app.db.models.enums import (
    ApplicationStatus,
    AvailabilityStatus,
    CompanyStatus,
    JobStatus,
)
from app.db.session import get_session
from app.indicators.schemas.indicator_filters import IndicatorFilters
from app.indicators.schemas.platform_indicators import PlatformIndicators
from app.indicators.services.platform_indicators import get_platform_indicators

router = APIRouter(
    prefix="/indicators",
    tags=["indicators"],
    dependencies=[Depends(require_administrator)],
    responses={code: PROBLEM_RESPONSE for code in (401, 403, 422, 503)},
)


@router.get("", response_model=PlatformIndicators)
def read_platform_indicators(
    session: Annotated[Session, Depends(get_session)],
    response: Response,
    start_date: Annotated[
        date | None,
        Query(description="First day of the period (UTC, inclusive)."),
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="Last day of the period (UTC, inclusive)."),
    ] = None,
    candidate_availability: Annotated[
        AvailabilityStatus | None,
        Query(description="Restricts candidate-based indicators."),
    ] = None,
    company_status: Annotated[
        CompanyStatus | None,
        Query(description="Restricts the company count."),
    ] = None,
    job_status: Annotated[
        JobStatus | None,
        Query(description="Restricts the job count."),
    ] = None,
    application_status: Annotated[
        ApplicationStatus | None,
        Query(description="Restricts the application and match counts."),
    ] = None,
) -> PlatformIndicators:
    filters = IndicatorFilters(
        start_date=start_date,
        end_date=end_date,
        candidate_availability=candidate_availability,
        company_status=company_status,
        job_status=job_status,
        application_status=application_status,
    )
    response.headers["Cache-Control"] = "no-store"
    return get_platform_indicators(session, filters)
