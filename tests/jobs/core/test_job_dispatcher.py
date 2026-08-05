from __future__ import annotations

from dataclasses import dataclass

from expanse.jobs.core.job import Job
from expanse.jobs.core.job_dispatcher import JobDispatcher
from expanse.jobs.stamps.job import JobStamp
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.sensitive import SensitiveStamp
from expanse.messenger.stamps.transport import TransportStamp
from expanse.messenger.stamps.unique import UniqueStamp
from expanse.support._utils import class_to_name


@dataclass
class Payload:
    value: str


class MyJob(Job[Payload]):
    pass


def test_prepare_wraps_payload_in_envelope() -> None:
    dispatcher = JobDispatcher()
    job = MyJob(Payload("hello"))
    envelope = dispatcher.prepare(job)

    assert envelope.open() == Payload("hello")


def test_prepare_adds_job_stamp() -> None:
    dispatcher = JobDispatcher()
    job = MyJob(Payload("hello"))
    envelope = dispatcher.prepare(job)

    assert envelope.has_stamp(JobStamp)


def test_prepare_job_stamp_contains_qualified_class_name() -> None:
    dispatcher = JobDispatcher()
    job = MyJob(Payload("hello"))
    envelope = dispatcher.prepare(job)

    stamp = envelope.stamp(JobStamp)
    assert stamp is not None
    assert stamp.job == class_to_name(MyJob)


def test_prepare_with_no_options_has_no_delay_stamp() -> None:
    dispatcher = JobDispatcher()
    job = MyJob(Payload("hello"))
    envelope = dispatcher.prepare(job)

    assert not envelope.has_stamp(DelayStamp)


def test_prepare_with_no_options_has_no_transport_stamp() -> None:
    dispatcher = JobDispatcher()
    job = MyJob(Payload("hello"))
    envelope = dispatcher.prepare(job)

    assert not envelope.has_stamp(TransportStamp)


def test_prepare_with_delay_adds_delay_stamp() -> None:
    dispatcher = JobDispatcher()
    job = MyJob(Payload("hello"))
    job.delay(30)
    envelope = dispatcher.prepare(job)

    assert envelope.has_stamp(DelayStamp)


def test_prepare_delay_is_converted_to_milliseconds() -> None:
    dispatcher = JobDispatcher()
    job = MyJob(Payload("hello"))
    job.delay(30)
    envelope = dispatcher.prepare(job)

    stamp = envelope.stamp(DelayStamp)
    assert stamp is not None
    assert stamp.delay == 30 * 1000


def test_prepare_with_via_adds_transport_stamp() -> None:
    dispatcher = JobDispatcher()
    job = MyJob(Payload("hello"))
    job.via("custom_transport")
    envelope = dispatcher.prepare(job)

    assert envelope.has_stamp(TransportStamp)


def test_prepare_via_stamp_contains_transport_name() -> None:
    dispatcher = JobDispatcher()
    job = MyJob(Payload("hello"))
    job.via("custom_transport")
    envelope = dispatcher.prepare(job)

    stamp = envelope.stamp(TransportStamp)
    assert stamp is not None
    assert stamp.name == "custom_transport"


def test_prepare_with_delay_and_via_adds_both_stamps() -> None:
    dispatcher = JobDispatcher()
    job = MyJob(Payload("hello"))
    job.delay(10).via("my_transport")
    envelope = dispatcher.prepare(job)

    assert envelope.has_stamp(DelayStamp)
    assert envelope.has_stamp(TransportStamp)


def test_prepare_each_call_produces_independent_envelope() -> None:
    dispatcher = JobDispatcher()
    envelope1 = dispatcher.prepare(MyJob(Payload("first")))
    envelope2 = dispatcher.prepare(MyJob(Payload("second")))

    assert envelope1.open() == Payload("first")
    assert envelope2.open() == Payload("second")


def test_prepare_does_not_mutate_job_options() -> None:
    dispatcher = JobDispatcher()
    job = MyJob(Payload("hello"))
    job.delay(5)

    dispatcher.prepare(job)
    dispatcher.prepare(job)

    stamp = dispatcher.prepare(job).stamp(DelayStamp)
    assert stamp is not None
    assert stamp.delay == 5 * 1000


def test_prepare_with_no_options_has_no_unique_stamp() -> None:
    dispatcher = JobDispatcher()
    job = MyJob(Payload("hello"))
    envelope = dispatcher.prepare(job)

    assert not envelope.has_stamp(UniqueStamp)


def test_prepare_with_unique_false_does_not_add_unique_stamp() -> None:
    dispatcher = JobDispatcher()
    job = MyJob(Payload("hello"))
    job.options["unique"] = False
    envelope = dispatcher.prepare(job)

    assert not envelope.has_stamp(UniqueStamp)


def test_prepare_with_unique_true_adds_unique_stamp() -> None:
    dispatcher = JobDispatcher()
    job = MyJob(Payload("hello"))
    job.options["unique"] = True
    envelope = dispatcher.prepare(job)

    assert envelope.has_stamp(UniqueStamp)


def test_prepare_with_sensitive_false_does_not_add_sensitive_stamp() -> None:
    dispatcher = JobDispatcher()
    job = MyJob(Payload("hello"))
    job.options["sensitive"] = False
    envelope = dispatcher.prepare(job)

    assert not envelope.has_stamp(SensitiveStamp)


def test_prepare_with_sensitive_true_adds_sensitive_stamp() -> None:
    dispatcher = JobDispatcher()
    job = MyJob(Payload("hello"))
    job.options["sensitive"] = True
    envelope = dispatcher.prepare(job)

    assert envelope.has_stamp(SensitiveStamp)
