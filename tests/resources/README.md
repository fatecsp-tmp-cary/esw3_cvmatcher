# Job Source Fixture Documentation

This fixture represents a sample response payload from the external job source (GitHub Vagas / apibr) used for offline testing and integration.

## File Location
`tests/resources/jobs_fixture.json`

## Expected Structure

| Field | Type | Description |
|---|---|---|
| `id` | Integer | Unique identifier of the job post |
| `title` | String | Job title including location/level if present |
| `url` | String | Source URL of the job posting |
| `labels` | Array[Object] | List of tags/skills associated with the job |
| `created_at` | String (ISO 8601) | Timestamp when the job post was created |
| `body` | String | Full markdown text containing job description and requirements |