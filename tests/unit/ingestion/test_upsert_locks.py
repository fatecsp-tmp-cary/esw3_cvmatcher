"""The largest permitted scan uses a bounded, consistently ordered lock set."""

from src.ingestion.upsert import lock_job_identities


def test_full_scan_locks_are_bounded_unique_and_independent_of_source_order():
    class RecordingSession:
        def __init__(self):
            self.locks = []

        def execute(self, statement):
            self.locks.append(tuple(statement.compile().params.values()))

    identities = [("platform", str(index)) for index in range(100_000)]
    forward, reverse = RecordingSession(), RecordingSession()
    lock_job_identities(forward, identities)
    lock_job_identities(reverse, reversed(identities))
    assert forward.locks == reverse.locks
    assert len(forward.locks) == len(set(forward.locks)) == 256
    assert [key for namespace, key in forward.locks] == list(range(256))
