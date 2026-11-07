# Job Source Fixture Documentation

`jobs_fixture.json` is the historical captured **GitHub issue** payload. It
contains GitHub-only fields, including `state`; it must not be treated as
evidence that APiBR supplies those fields.

`apibr_issues.json` is a small synthetic fixture for the state-free case raised
in PR reviews #101/#106. It deliberately omits `state` and uses HTML section
boundaries. It is not a newly captured or independently verified APiBR response.
Its ingestion test forbids network access and expects `DISCOVERED`, not `ACTIVE`.
Live APiBR shape/completeness verification remains in issue #113; the endpoint
closed the connection during the 2026-11-07 audit.

## File Location
`tests/resources/jobs_fixture.json`

## Expected Structure

| Field | Type | Description |
|---|---|---|
| `url` | String | API endpoint URL of the issue |
| `repository_url` | String | API URL of the parent repository |
| `html_url` | String | Web URL of the job posting |
| `id` | Integer | Unique identifier of the issue |
| `node_id` | String | GraphQL global node ID |
| `number` | Integer | Issue number within the repository |
| `title` | String | Job title and location summary |
| `user` | Object | User profile details of the poster |
| `labels` | Array[Object] | Associated tags/skills |
| `state` | String | Status of the issue (`open`/`closed`) |
| `locked` | Boolean | Lock status of the thread |
| `created_at` | String (ISO 8601) | Timestamp when job post was created |
| `updated_at` | String (ISO 8601) | Timestamp when job post was last updated |
| `body` | String | Full markdown text of the job post |
| `reactions` | Object | Reaction count metrics |
