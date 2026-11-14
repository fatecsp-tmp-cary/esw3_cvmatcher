# Job Source Fixture Documentation

`jobs_fixture.json` is a captured **GitHub issue** payload. It
contains GitHub-only fields, including `state`; it must not be treated as
evidence that APiBR supplies those fields.

`apibr_issues.json` is a small synthetic fixture for state-free records. It deliberately omits `state` and uses HTML section
boundaries. It is not a captured or independently verified APiBR response.
Its ingestion test forbids network access and expects `ACTIVE` under ADR-014:
presence in the listing is the availability evidence, without any per-job request.
Live APiBR shape/completeness verification remains in issue #113.

`apibr_v2_issues.json` is a synthetic fixture that mirrors the response shape
observed from `GET /vagas/api/v2/issues` on 2026-11-12: typed label objects
(`label`, `APIBr`, `topic`), title-derived `keywords`, and no `state`. All titles,
bodies, users and repositories are invented; no source record is retained. It
covers explicit, decorated, conflicting and topic-only label metadata.

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
