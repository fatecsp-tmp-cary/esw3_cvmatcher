# Contributing to CV-Match

Thank you for contributing to CV-Match. The project is building an open-source,
local-first API that matches structured CV data with jobs from multiple sources.
Please read this guide and the project [implementation plan](PLAN.md) before
opening an issue or pull request.

## Before you start

- Search existing issues and pull requests before opening a new one.
- For larger changes, open an issue first so the scope and design can be
  discussed.
- Do not include real CVs, personal data, credentials, API keys, or other
  secrets in issues, pull requests, fixtures, logs, or test data.
- Keep changes focused. Update directly related documentation and tests with
  the implementation.

## Development workflow

1. Create or select an issue describing the problem or proposed change.
2. Create a branch using this format:

   ```text
   feat_<issue-number>_<short-description>
   task_<issue-number>_<short-description>
   bug_<issue-number>_<short-description>
   ```

   For example: `feat_42_source-adapter`.
3. Implement the change in the smallest coherent set of commits.
4. Add or update tests for changed behavior.
5. Open a pull request using the repository pull request template and link the
   related issue.

Pull requests are checked automatically for the required branch-name format.
Use lowercase words separated by hyphens or underscores in the description;
avoid spaces and shell-special characters.

## Project conventions

Please preserve these architectural boundaries:

- Keep ingestion, normalization, indexing, matching/ranking, persistence, and
  API responsibilities separate.
- Put source-specific behavior behind a common ingestion interface; do not
  couple the domain model to an external source format.
- Treat each source-specific job as independent. Do not add cross-source
  deduplication or merging.
- Keep candidate profiles, embeddings, and match results request-scoped.
  Never persist or log them, including in exceptions, tracing, or telemetry.
- Keep geographic eligibility filtering out of matching. Location and mode may
  be normalized and represented, but they must not be used for geographic
  eligibility classification or filtering.
- Preserve deterministic ranking for identical normalized inputs, data, model
  and algorithm versions.
- Respect source terms, rate limits, robots/access restrictions, and storage
  restrictions.

When a change affects persisted data, API contracts, source identity,
normalization, matching, or ranking, describe the compatibility and migration
impact in the pull request.

## Testing and validation

The project requires unit, integration, API, and end-to-end coverage as the
corresponding components become available. Prefer deterministic fixtures over
live external services; live-source tests are optional and must not be required
for CI.

At minimum, changes should cover the behavior they modify. Important regression
areas include:

- normalization, taxonomy, identity, hashing, and lifecycle transitions;
- requirement extraction, filtering, scoring, and deterministic ranking;
- source failures, incremental versus snapshot ingestion, expiration, and
  reactivation;
- embedding regeneration after job-content or model-version changes; and
- the explicit no-deduplication and no-geographic-filtering rules.

Run the project’s configured formatter, linter, type checker, and test commands
before submitting a pull request. If the relevant tooling is not available yet,
document the validation performed and any limitation in the pull request.

## Pull requests

A good pull request:

- explains what changed and why;
- links the issue it addresses;
- includes tests or explains why tests are not applicable;
- documents API, schema, migration, configuration, or behavioral changes;
- calls out risks, limitations, and follow-up work; and
- contains no unrelated formatting or generated-file changes.

Reviewers may request changes to preserve the project’s architecture,
privacy requirements, deterministic behavior, or source-usage constraints.

## Reporting bugs and proposing features

Use the repository issue templates. Include a minimal reproduction, expected
behavior, actual behavior, and relevant logs or fixtures after removing
sensitive data. Feature requests should explain the use case, proposed scope,
constraints, and how success would be validated.

For security issues, do not open a public issue with exploitable details or
personal data. Report them privately through the repository’s configured
security contact.
