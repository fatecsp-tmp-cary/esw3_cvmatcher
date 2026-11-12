"""Operator command that registers a supported job source in PostgreSQL.

Source configuration is a deliberate operator action: nothing seeds a source
automatically. This module needs only the database; it never loads a model.
"""

import argparse
import json
import logging
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.ingestion.adapters import PollingMode
from src.persistence.database import create_db_engine, create_session_factory
from src.persistence.job.job_source import JobSource

# Names with a registered poller in ``SourceScheduler``.
SUPPORTED_SOURCES = ("apibr",)

logger = logging.getLogger(__name__)


def register_source(
    session: Session,
    name: str,
    *,
    polling_mode: str = PollingMode.INCREMENTAL.value,
    enabled: bool = True,
) -> tuple[int, bool]:
    """Create or update a supported source; return its ID and whether it was created.

    The operation is idempotent by case-insensitive name. Scheduling timestamps
    and run history of an existing source are preserved.
    """
    key = name.strip().casefold() if isinstance(name, str) else ""
    if key not in SUPPORTED_SOURCES:
        raise ValueError("unsupported source")
    mode = PollingMode(polling_mode)
    source = session.scalar(select(JobSource).where(func.lower(JobSource.name) == key))
    created = source is None
    if source is None:
        source = JobSource(name=key, type="api", polling_mode=mode.value, enabled=enabled)
        session.add(source)
    else:
        source.polling_mode = mode.value
        source.enabled = enabled
    session.flush()
    return source.id, created


def main(
    argv: Sequence[str] | None = None,
    *,
    sessions: Callable[[], AbstractContextManager[Session]] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.worker.sources", description="Manage CV-Match job sources"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    register = commands.add_parser("register", help="Create or update a supported source")
    register.add_argument("name", choices=SUPPORTED_SOURCES)
    register.add_argument(
        "--polling-mode",
        choices=[mode.value for mode in PollingMode],
        default=PollingMode.INCREMENTAL.value,
    )
    register.add_argument("--disabled", action="store_true", help="Register without polling")
    args = parser.parse_args(argv)
    try:
        factory = sessions or create_session_factory(create_db_engine())
        with factory() as session:
            source_id, created = register_source(
                session, args.name, polling_mode=args.polling_mode, enabled=not args.disabled
            )
            session.commit()
    except Exception:
        # Never format exceptions: connection strings may occur in driver messages.
        logger.error(json.dumps({"event": "source_registration_failed"}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "event": "source_registered",
                "source_id": source_id,
                "created": created,
                "polling_mode": args.polling_mode,
                "enabled": not args.disabled,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
