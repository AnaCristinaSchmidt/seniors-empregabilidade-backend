# Platform indicators

`GET /api/v1/indicators` aggregates platform indicators for administrators
(CU-86e3ke4qv, US-24-T01). The endpoint requires an administrator account and
answers with `Cache-Control: no-store`.

## Filters

All filters are optional query parameters and combine with AND.

| Parameter | Type | Applies to |
|---|---|---|
| `start_date` | date | Every indicator. First day of the period, inclusive. |
| `end_date` | date | Every indicator. Last day of the period, inclusive. |
| `candidate_availability` | `AvailabilityStatus` | Candidates and both candidate segments. |
| `company_status` | `CompanyStatus` | Companies. |
| `job_status` | `JobStatus` | Jobs. |
| `application_status` | `ApplicationStatus` | Applications and matches. |

A status filter only restricts the entity it belongs to. Filtering by
`company_status` does not change the job count, for example.

`start_date` after `end_date` fails with `422` and the stable code
`invalid_period`. Unknown status values fail with the standard validation
error.

## Period semantics

The period is a half-open interval in UTC: `start_date 00:00:00` inclusive up to
`end_date + 1 day 00:00:00` exclusive. Omitting one bound leaves that side open.
Every entity is dated by the moment it was registered on the platform:

| Entity | Reference date |
|---|---|
| Candidate | `app_user.created_at` of the candidate's account |
| Company | `app_user.created_at` of the company's account |
| Job | `job.created_at` |
| Application | `application.created_at` |

## Totals

| Field | Rule |
|---|---|
| `candidates` | Rows of `candidate` matching the filters. |
| `companies` | Rows of `company` matching the filters, in any status unless filtered. |
| `jobs` | Rows of `job` matching the filters, drafts included unless filtered. |
| `applications` | Rows of `application` matching the filters. |
| `matches` | Applications with a non-null `match_score`. Respects the application filters. |

Account status (`active`, `suspended`, `blocked`) does not exclude anyone from
the counts.

## Segments

Both segments count candidates and respect the period and
`candidate_availability`.

| Field | Rule |
|---|---|
| `candidates_without_placement` | Candidates with no application in status `hired`, on any job and at any date. |
| `incomplete_resumes` | Candidates with no resume yet, or with `resume.completion_percentage` below 100. |

Placement is a lasting fact about the candidate, so the `hired` check ignores
the period and `application_status`. The self-declared
`resume.employment_status` is not used.

## Response

```json
{
  "filters": {
    "start_date": "2026-01-01",
    "end_date": "2026-01-31",
    "candidate_availability": null,
    "company_status": null,
    "job_status": null,
    "application_status": null
  },
  "totals": {
    "candidates": 0,
    "companies": 0,
    "jobs": 0,
    "applications": 0,
    "matches": 0
  },
  "segments": {
    "candidates_without_placement": 0,
    "incomplete_resumes": 0
  }
}
```

`filters` echoes what was applied, so a consumer can tell an unfiltered answer
from a filtered one.

## Tests

`tests/indicators/test_platform_indicators.py` runs against PostgreSQL and needs
`RUN_DATABASE_INTEGRATION_TESTS=1`. It builds its data in January 2001 and
asserts exact counts for that window, so it assumes the database holds no
records created in that month.
