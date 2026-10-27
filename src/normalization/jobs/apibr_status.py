"""Availability checks for APiBR's GitHub issue URLs."""

import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from src.persistence.job.job import JobStatus

_GITHUB_ISSUE_PATH = re.compile(r"^/([^/]+)/([^/]+)/issues/([1-9][0-9]*)/?$")
_TIMEOUT_SECONDS = 10


def _github_api_url(job_url: str) -> str | None:
    """Convert a canonical GitHub issue URL to its API endpoint safely."""
    try:
        parsed = urlsplit(job_url)
    except ValueError:
        return None

    hostname = (parsed.hostname or "").casefold()
    if parsed.scheme != "https" or hostname not in {"github.com", "api.github.com"}:
        return None
    path = parsed.path
    if hostname == "api.github.com":
        prefix = "/repos"
        if not path.startswith(prefix):
            return None
        path = path[len(prefix) :]
    match = _GITHUB_ISSUE_PATH.fullmatch(path)
    if match is None:
        return None
    owner, repository, issue_number = match.groups()
    return f"https://api.github.com/repos/{owner}/{repository}/issues/{issue_number}"


def check_apibr_job_status(job_url: str | None) -> JobStatus | None:
    """Return a confirmed APiBR issue status; unknown/transient results are None.

    The normalizer already maps source-provided ``state=closed`` to EXPIRED.
    This check supports later verification from the stored descriptive URL.
    A None result must not update lifecycle or ``last_verified_at``.
    """
    if not isinstance(job_url, str):
        return None
    api_url = _github_api_url(job_url)
    if api_url is None:
        return None

    request = Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "cv-match-apibr-verifier",
        },
    )
    try:
        with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            if not 200 <= response.status < 300:
                return None
            payload = json.loads(response.read())
    except HTTPError as error:
        if error.code in {404, 410}:
            return JobStatus.EXPIRED
        return None
    except (URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None
    if payload.get("state") == "closed":
        return JobStatus.EXPIRED
    if payload.get("state") == "open":
        return JobStatus.ACTIVE
    return None
