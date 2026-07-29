from __future__ import annotations

import pytest

from expanse.jobs.core.job import Job
from expanse.jobs.decorators import delay
from expanse.jobs.decorators import transport
from expanse.jobs.decorators import unique


def test_delay_sets_class_options() -> None:
    @delay(30)
    class MyJob(Job[str]):
        pass

    job = MyJob("hello")

    assert job.options["delay"] == 30


def test_transport_sets_class_options() -> None:
    @transport("sqs")
    class MyJob(Job[str]):
        pass

    job = MyJob("hello")

    assert job.options["transport"] == "sqs"


def test_unique_sets_class_options() -> None:
    @unique()
    class MyJob(Job[str]):
        pass

    job = MyJob("hello")

    assert job.options["unique"] is True


def test_decorators_can_be_stacked() -> None:
    @unique()
    @delay(30)
    @transport("sqs")
    class MyJob(Job[str]):
        pass

    job = MyJob("hello")

    assert job.options["delay"] == 30
    assert job.options["transport"] == "sqs"
    assert job.options["unique"] is True


def test_decorator_merges_with_existing_class_options() -> None:
    @delay(30)
    class MyJob(Job[str]):
        options = {"transport": "sqs"}  # noqa: RUF012

    job = MyJob("hello")

    assert job.options["delay"] == 30
    assert job.options["transport"] == "sqs"


def test_decorator_does_not_mutate_base_class_options() -> None:
    class BaseJob(Job[str]):
        pass

    @delay(30)
    class MyJob(BaseJob):
        pass

    assert "delay" not in getattr(BaseJob, "options", {})
    assert MyJob("hello").options["delay"] == 30


def test_subclass_of_decorated_job_inherits_options() -> None:
    @delay(30)
    class BaseJob(Job[str]):
        pass

    class MyJob(BaseJob):
        pass

    assert MyJob("hello").options["delay"] == 30


def test_instance_methods_override_decorator_defaults() -> None:
    @delay(30)
    @transport("sqs")
    class MyJob(Job[str]):
        pass

    job = MyJob("hello").delay(60).via("sns")

    assert job.options["delay"] == 60
    assert job.options["transport"] == "sns"


def test_delay_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        delay(-1)


def test_transport_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="empty"):
        transport("")
