# Job Source Fixture Documentation

This fixture represents a sample response payload from the external job source (GitHub Vagas / apibr) used for offline testing and integration.

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
