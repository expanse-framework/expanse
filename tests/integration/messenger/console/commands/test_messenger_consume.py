from __future__ import annotations

import asyncio
import signal

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from expanse.messenger.worker import Worker


if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture

    from expanse.core.application import Application
    from expanse.testing.command_tester import CommandTester


@pytest.fixture()
def _mock_signal_handlers(mocker: MockerFixture) -> None:
    """Patch add/remove_signal_handler on the event loop class.

    The command tester runs in a non-main thread via anyio, which prevents
    real signal handler registration.  Patching at the class level lets the
    command execute without errors while still allowing tests to inspect the
    calls via mocker's spy/patch.
    """
    import asyncio

    loop_cls = asyncio.get_event_loop().__class__

    mocker.patch.object(loop_cls, "add_signal_handler", return_value=None)
    mocker.patch.object(loop_cls, "remove_signal_handler", return_value=True)


@pytest.fixture()
def mock_worker(app: Application) -> AsyncMock:
    worker = AsyncMock(spec=Worker)
    app.container.instance(Worker, worker)

    return worker


@pytest.mark.usefixtures("_mock_signal_handlers")
async def test_command_runs_worker_with_default_transport(
    command_tester: CommandTester,
    mock_worker: AsyncMock,
) -> None:
    command = command_tester.command("messenger consume")
    command.run()

    mock_worker.run.assert_awaited_once_with(
        transport_name=None, limit=None, sleep=1000
    )


@pytest.mark.usefixtures("_mock_signal_handlers")
async def test_command_runs_worker_with_specified_transport(
    command_tester: CommandTester,
    mock_worker: AsyncMock,
) -> None:
    command = command_tester.command("messenger consume")
    command.run("database")

    mock_worker.run.assert_awaited_once_with(
        transport_name="database", limit=None, sleep=1000
    )


@pytest.mark.usefixtures("_mock_signal_handlers")
async def test_command_passes_limit_to_worker(
    command_tester: CommandTester,
    mock_worker: AsyncMock,
) -> None:
    command = command_tester.command("messenger consume")
    command.run("--limit 10")

    mock_worker.run.assert_awaited_once_with(transport_name=None, limit=10, sleep=1000)


@pytest.mark.usefixtures("_mock_signal_handlers")
async def test_command_passes_sleep_to_worker(
    command_tester: CommandTester,
    mock_worker: AsyncMock,
) -> None:
    command = command_tester.command("messenger consume")
    command.run("--sleep 5")

    mock_worker.run.assert_awaited_once_with(
        transport_name=None, limit=None, sleep=5000
    )


@pytest.mark.usefixtures("_mock_signal_handlers")
async def test_command_outputs_consuming_message_for_named_transport(
    command_tester: CommandTester,
    mock_worker: AsyncMock,
) -> None:
    command = command_tester.command("messenger consume")
    command.run("database")

    output = command.output.fetch()

    assert "database" in output


@pytest.mark.usefixtures("_mock_signal_handlers")
async def test_command_outputs_default_transport_when_none(
    command_tester: CommandTester,
    mock_worker: AsyncMock,
) -> None:
    command = command_tester.command("messenger consume")
    command.run()

    output = command.output.fetch()

    assert "default" in output


@pytest.mark.usefixtures("_mock_signal_handlers")
async def test_command_outputs_stop_condition_when_limit_is_set(
    command_tester: CommandTester,
    mock_worker: AsyncMock,
) -> None:
    command = command_tester.command("messenger consume")
    command.run("--limit 25")

    output = command.output.fetch()

    assert "25" in output
    assert "will stop" in output.lower()


@pytest.mark.usefixtures("_mock_signal_handlers")
async def test_command_outputs_ctrl_c_message(
    command_tester: CommandTester,
    mock_worker: AsyncMock,
) -> None:
    command = command_tester.command("messenger consume")
    command.run()

    output = command.output.fetch()

    assert "Ctrl+C" in output


@pytest.mark.usefixtures("_mock_signal_handlers")
async def test_command_does_not_output_stop_condition_without_limit(
    command_tester: CommandTester,
    mock_worker: AsyncMock,
) -> None:
    command = command_tester.command("messenger consume")
    command.run()

    output = command.output.fetch()

    assert "will stop" not in output.lower()


async def test_command_registers_sigint_and_sigterm_handlers(
    command_tester: CommandTester,
    mock_worker: AsyncMock,
    mocker: MockerFixture,
) -> None:
    registered: dict[int, Callable[..., object]] = {}

    def add_signal_handler(
        self: object, sig: int, callback: Callable[..., object], *args: object
    ) -> None:
        registered[sig] = callback

    loop_cls = asyncio.get_event_loop().__class__
    mocker.patch.object(loop_cls, "add_signal_handler", add_signal_handler)
    mocker.patch.object(loop_cls, "remove_signal_handler", return_value=True)

    command = command_tester.command("messenger consume")
    command.run()

    assert signal.SIGINT in registered
    assert signal.SIGTERM in registered


async def test_command_signal_handler_stops_worker(
    command_tester: CommandTester,
    mock_worker: AsyncMock,
    mocker: MockerFixture,
) -> None:
    import asyncio.unix_events

    registered: dict[int, Callable[..., object]] = {}

    def add_signal_handler(
        self: object, sig: int, callback: Callable[..., object], *args: object
    ) -> None:
        registered[sig] = callback

    loop_cls = asyncio.get_event_loop().__class__
    mocker.patch.object(loop_cls, "add_signal_handler", add_signal_handler)
    mocker.patch.object(loop_cls, "remove_signal_handler", return_value=True)

    async def run_and_trigger_stop(**kwargs: object) -> None:
        registered[signal.SIGINT]()

    mock_worker.run.side_effect = run_and_trigger_stop

    command = command_tester.command("messenger consume")
    command.run()

    mock_worker.stop.assert_called_once()


async def test_command_signal_handler_removes_handlers_after_stop(
    command_tester: CommandTester,
    mock_worker: AsyncMock,
    mocker: MockerFixture,
) -> None:
    import asyncio.unix_events

    registered: dict[int, Callable[..., object]] = {}
    removed_signals: list[int] = []

    def add_signal_handler(
        self: object, sig: int, callback: Callable[..., object], *args: object
    ) -> None:
        registered[sig] = callback

    def remove_signal_handler(self: object, sig: int) -> bool:
        removed_signals.append(sig)
        return True

    loop_cls = asyncio.get_event_loop().__class__
    mocker.patch.object(loop_cls, "add_signal_handler", add_signal_handler)
    mocker.patch.object(loop_cls, "remove_signal_handler", remove_signal_handler)

    async def run_and_trigger_stop(**kwargs: object) -> None:
        registered[signal.SIGTERM]()

    mock_worker.run.side_effect = run_and_trigger_stop

    command = command_tester.command("messenger consume")
    command.run()

    assert signal.SIGINT in removed_signals
    assert signal.SIGTERM in removed_signals
