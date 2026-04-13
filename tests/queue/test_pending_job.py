from __future__ import annotations

from dataclasses import dataclass

from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.self_handling import SelfHandlingStamp
from expanse.queue.pending_job import PendingJob


@dataclass
class MyJob:
    value: str

    def handle(self) -> None:
        pass


def test_job_is_wrapped_in_envelope() -> None:
    job = MyJob(value="test")
    pending = PendingJob(job)

    assert pending._job.open() is job


def test_envelope_has_self_handling_stamp() -> None:
    job = MyJob(value="test")
    pending = PendingJob(job)

    assert pending._job.has_stamp(SelfHandlingStamp)


def test_delay_returns_self_for_chaining() -> None:
    job = MyJob(value="test")
    pending = PendingJob(job)

    result = pending.delay(5)

    assert result is pending


def test_delay_adds_delay_stamp() -> None:
    job = MyJob(value="test")
    pending = PendingJob(job)

    pending.delay(10)

    assert pending._job.has_stamp(DelayStamp)


def test_delay_stamp_value_is_converted_to_milliseconds() -> None:
    job = MyJob(value="test")
    pending = PendingJob(job)

    pending.delay(10)

    stamp = pending._job.stamp(DelayStamp)
    assert stamp is not None
    assert stamp.delay == 10 * 1000


def test_delay_preserves_self_handling_stamp() -> None:
    job = MyJob(value="test")
    pending = PendingJob(job)

    pending.delay(5)

    assert pending._job.has_stamp(SelfHandlingStamp)


def test_delay_can_be_chained() -> None:
    job = MyJob(value="test")

    # Chaining: each call to delay overwrites the previous stamp (same key)
    result = PendingJob(job).delay(5).delay(10)

    stamp = result._job.stamp(DelayStamp)
    assert stamp is not None
    assert stamp.delay == 10 * 1000
