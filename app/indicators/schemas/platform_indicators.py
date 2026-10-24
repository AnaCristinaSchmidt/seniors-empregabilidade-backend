from datetime import date

from pydantic import BaseModel, ConfigDict

from app.db.models.enums import (
    ApplicationStatus,
    AvailabilityStatus,
    CompanyStatus,
    JobStatus,
)


class AppliedFilters(BaseModel):
    model_config = ConfigDict(frozen=True)

    start_date: date | None
    end_date: date | None
    candidate_availability: AvailabilityStatus | None
    company_status: CompanyStatus | None
    job_status: JobStatus | None
    application_status: ApplicationStatus | None


class IndicatorTotals(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidates: int
    companies: int
    jobs: int
    applications: int
    matches: int


class IndicatorSegments(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidates_without_placement: int
    incomplete_resumes: int


class PlatformIndicators(BaseModel):
    model_config = ConfigDict(frozen=True)

    filters: AppliedFilters
    totals: IndicatorTotals
    segments: IndicatorSegments
