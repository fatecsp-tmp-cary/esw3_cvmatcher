"""Request-local cooperative budgets; no curriculum values enter this state."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from threading import BoundedSemaphore, Event
from time import monotonic


class ProcessingUnavailable(Exception):
    """A fixed-category processing budget failure, without submitted values."""


@dataclass(frozen=True)
class Deadline:
    expires_at: float
    clock: Callable[[], float]
    cancelled: Event | None = None

    def check(self) -> None:
        if self.cancelled is not None and self.cancelled.is_set():
            raise ProcessingUnavailable("cancelled")
        if self.clock() >= self.expires_at:
            raise ProcessingUnavailable("deadline")


_current: ContextVar[Deadline | None] = ContextVar("matching_deadline", default=None)


def checkpoint() -> None:
    """Native inference finishes before the following checkpoint can cancel it."""
    deadline = _current.get()
    if deadline is not None:
        deadline.check()


class RequestBudget:
    def __init__(self, *, clock: Callable[[], float] = monotonic):
        self.clock = clock
        self._slot = BoundedSemaphore(1)

    @contextmanager
    def admit(self, *, cancelled: Event | None = None) -> Iterator[None]:
        if not self._slot.acquire(blocking=False):
            raise ProcessingUnavailable("busy")
        token = _current.set(Deadline(self.clock() + 30.0, self.clock, cancelled))
        try:
            checkpoint()
            yield
            checkpoint()
        finally:
            _current.reset(token)
            self._slot.release()
