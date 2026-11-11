from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import text

from src.api.rate_limit import GlobalRateLimiter


def test_limit_is_shared_across_instances_and_connections(db_engine):
    # Longer window keeps this concurrency regression independent of machine speed.
    with db_engine.begin() as connection:
        connection.execute(text("DELETE FROM api_admissions"))
    try:
        limiters = [GlobalRateLimiter(db_engine, limit=10, seconds=60) for _ in range(24)]
        with ThreadPoolExecutor(max_workers=6) as pool:
            assert sum(pool.map(lambda limiter: limiter.allow(), limiters)) == 10
        with db_engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE api_admissions SET admitted_at = "
                    "clock_timestamp() - interval '61 seconds'"
                )
            )
        assert limiters[0].allow()
        with db_engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM api_admissions")) == 1
    finally:
        with db_engine.begin() as connection:
            connection.execute(text("DELETE FROM api_admissions"))


def test_default_quota_retains_admissions_older_than_one_second(db_engine):
    with db_engine.begin() as connection:
        connection.execute(text("DELETE FROM api_admissions"))
        connection.execute(
            text(
                "INSERT INTO api_admissions (admitted_at) "
                "SELECT clock_timestamp() - interval '2 seconds' FROM generate_series(1, 60)"
            )
        )
    try:
        assert not GlobalRateLimiter(db_engine).allow()
        with db_engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE api_admissions SET admitted_at = "
                    "clock_timestamp() - interval '61 seconds'"
                )
            )
        assert GlobalRateLimiter(db_engine).allow()
    finally:
        with db_engine.begin() as connection:
            connection.execute(text("DELETE FROM api_admissions"))
