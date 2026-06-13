from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from anyio.to_thread import run_sync

from expanse.container.container import Container
from expanse.core.helpers import _set_container
from expanse.jobs.asynchronous.job_dispatcher import JobDispatcher as AsyncJobDispatcher
from expanse.jobs.core.job import Job
from expanse.jobs.synchronous.job_dispatcher import JobDispatcher as SyncJobDispatcher


if TYPE_CHECKING:
    from collections.abc import Generator

    from pytest_mock import MockerFixture


class MyJob(Job[str]):
    pass


@pytest.fixture(autouse=True)
def reset_container() -> Generator[None, None, None]:
    yield
    _set_container(None)


async def test_dispatch_delegates_to_async_dispatcher(mocker: MockerFixture) -> None:
    job = MyJob("hello")
    mock_dispatcher = mocker.AsyncMock(spec=AsyncJobDispatcher)

    container = Container()
    container.instance(AsyncJobDispatcher, mock_dispatcher)
    _set_container(container)

    await job.dispatch()

    mock_dispatcher.dispatch.assert_called_once_with(job)


async def test_dispatch_raises_when_container_not_set() -> None:
    job = MyJob("hello")

    with pytest.raises(RuntimeError, match="Container not set"):
        await job.dispatch()


async def test_dispatch_sync_delegates_to_sync_dispatcher(
    mocker: MockerFixture,
) -> None:
    job = MyJob("hello")
    mock_dispatcher = mocker.MagicMock(spec=SyncJobDispatcher)

    container = Container()
    container.instance(SyncJobDispatcher, mock_dispatcher)
    _set_container(container)

    # dispatch_sync() uses async_to_sync(), which requires a running anyio event loop
    # in the calling thread — use anyio.to_thread.run_sync() to satisfy that contract.
    await run_sync(job.dispatch_sync)

    mock_dispatcher.dispatch.assert_called_once_with(job)


def test_dispatch_sync_raises_when_container_not_set() -> None:
    job = MyJob("hello")

    # _get_container() is called before async_to_sync(), so the error is raised
    # synchronously without needing to be inside an anyio thread.
    with pytest.raises(RuntimeError, match="Container not set"):
        job.dispatch_sync()


def test_payload_is_stored_on_init() -> None:
    job = MyJob("hello")

    assert job.payload == "hello"


def test_options_are_empty_by_default() -> None:
    job = MyJob("hello")

    assert job.options == {}


def test_each_instance_has_independent_options() -> None:
    job1 = MyJob("a")
    job2 = MyJob("b")
    job1.via("transport_a")

    assert "transport" not in job2.options


def test_delay_sets_options_delay() -> None:
    job = MyJob("test")
    job.delay(10)

    assert job.options["delay"] == 10


def test_via_sets_options_transport() -> None:
    job = MyJob("test")
    job.via("custom_transport")

    assert job.options["transport"] == "custom_transport"


def test_delay_returns_self_for_chaining() -> None:
    job = MyJob("test")

    assert job.delay(5) is job


def test_via_returns_self_for_chaining() -> None:
    job = MyJob("test")

    assert job.via("t") is job


def test_delay_and_via_can_be_chained() -> None:
    job = MyJob("test").delay(10).via("custom_transport")

    assert job.options["delay"] == 10
    assert job.options["transport"] == "custom_transport"


def test_delay_overwrites_previous_delay() -> None:
    job = MyJob("test")
    job.delay(5).delay(10)

    assert job.options["delay"] == 10


def test_via_overwrites_previous_transport() -> None:
    job = MyJob("test")
    job.via("first").via("second")

    assert job.options["transport"] == "second"
