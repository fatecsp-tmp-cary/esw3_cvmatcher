"""Local worker command; model/bootstrap construction is explicitly injectable."""

import argparse
import json
import logging
import signal
from collections.abc import Callable, Sequence
from threading import Event

from src.worker.bootstrap import (
    create_default_worker,
    import_default_meupadrinho,
    retry_default_extraction,
)
from src.worker.runtime import BackgroundWorker

logger = logging.getLogger(__name__)


def main(
    argv: Sequence[str] | None = None,
    *,
    worker_factory: Callable[[], BackgroundWorker] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description="Run local CV-Match background processing")
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--once", action="store_true", help="Run one bounded processing cycle")
    operation.add_argument(
        "--retry-extraction", type=int, metavar="JOB_ID", help="Explicitly requeue a stored job"
    )
    operation.add_argument(
        "--import-meupadrinho",
        type=str,
        metavar="PATH",
        help="Import a MeuPadrinho JSONL dump file into PostgreSQL",
    )
    args = parser.parse_args(argv)
    # Recovery and offline JSONL imports must work without serving model artifacts.
    if args.retry_extraction is not None and worker_factory is None:
        try:
            retry_default_extraction(args.retry_extraction)
            return 0
        except Exception:
            logger.error(json.dumps({"event": "worker_operation_failed"}, sort_keys=True))
            return 1
    if args.import_meupadrinho is not None and worker_factory is None:
        try:
            import_default_meupadrinho(args.import_meupadrinho)
            return 0
        except Exception:
            logger.error(json.dumps({"event": "worker_operation_failed"}, sort_keys=True))
            return 1
    try:
        worker = (worker_factory or create_default_worker)()
    except Exception:
        logger.error(json.dumps({"event": "worker_configuration_unavailable"}, sort_keys=True))
        return 1
    try:
        if args.retry_extraction is not None:
            worker.retry_extraction(args.retry_extraction)
            return 0
        if args.import_meupadrinho is not None:
            worker.import_meupadrinho(args.import_meupadrinho)
            return 0
        if args.once:
            return int(bool(worker.run_once().errors))
        stop = Event()

        def request_stop(_signum, _frame):
            stop.set()

        previous = {
            sig: signal.signal(sig, request_stop) for sig in (signal.SIGINT, signal.SIGTERM)
        }
        try:
            worker.run_forever(stop)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
        return 0
    except Exception:
        logger.error(json.dumps({"event": "worker_operation_failed"}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
