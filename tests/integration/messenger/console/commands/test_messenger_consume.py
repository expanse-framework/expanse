import asyncio
import signal

from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from expanse.messenger.console.commands.messenger_consume import MessengerConsumeCommand
from expanse.messenger.worker import Worker


@pytest.fixture()
def mock_loop() -> tuple[MagicMock, dict[int, object]]:
    """Create a mock event loop that captures signal handler registrations."""
    registered: dict[int, object] = {}
    loop = MagicMock()

    def add_signal_handler(sig: int, callback: object, *args: object) -> None:
        registered[sig] = callback

    def remove_signal_handler(sig: int) -> bool:
        return registered.pop(sig, None) is not None

    loop.add_signal_handler = add_signal_handler
    loop.remove_signal_handler = remove_signal_handler

    return loop, registered


@pytest.fixture()
def command() -> MessengerConsumeCommand:
    return MessengerConsumeCommand()


async def test_command_runs_worker_with_default_transport(
    command: MessengerConsumeCommand,
    mock_loop: tuple[MagicMock, dict[int, object]],
) -> None:
    mock_worker = AsyncMock(spec=Worker)
    loop, _ = mock_loop

    with (
        patch.object(command, "argument", return_value=None),
        patch.object(asyncio, "get_running_loop", return_value=loop),
    ):
        await command.handle(mock_worker)

    mock_worker.run.assert_awaited_once_with(transport_name=None)


async def test_command_runs_worker_with_specified_transport(
    command: MessengerConsumeCommand,
    mock_loop: tuple[MagicMock, dict[int, object]],
) -> None:
    mock_worker = AsyncMock(spec=Worker)
    loop, _ = mock_loop

    with (
        patch.object(command, "argument", return_value="database"),
        patch.object(asyncio, "get_running_loop", return_value=loop),
    ):
        await command.handle(mock_worker)

    mock_worker.run.assert_awaited_once_with(transport_name="database")


async def test_command_registers_sigint_and_sigterm_handlers(
    command: MessengerConsumeCommand,
    mock_loop: tuple[MagicMock, dict[int, object]],
) -> None:
    mock_worker = AsyncMock(spec=Worker)
    loop, registered = mock_loop

    with (
        patch.object(command, "argument", return_value=None),
        patch.object(asyncio, "get_running_loop", return_value=loop),
    ):
        await command.handle(mock_worker)

    assert signal.SIGINT in registered
    assert signal.SIGTERM in registered


async def test_command_signal_handler_stops_worker(
    command: MessengerConsumeCommand,
    mock_loop: tuple[MagicMock, dict[int, object]],
) -> None:
    mock_worker = AsyncMock(spec=Worker)
    loop, registered = mock_loop

    async def run_and_trigger_stop(transport_name: str | None = None) -> None:
        callback = registered[signal.SIGINT]
        callback()

    mock_worker.run.side_effect = run_and_trigger_stop

    with (
        patch.object(command, "argument", return_value=None),
        patch.object(asyncio, "get_running_loop", return_value=loop),
    ):
        await command.handle(mock_worker)

    mock_worker.stop.assert_called_once()


async def test_command_signal_handler_removes_handlers_after_stop(
    command: MessengerConsumeCommand,
    mock_loop: tuple[MagicMock, dict[int, object]],
) -> None:
    mock_worker = AsyncMock(spec=Worker)
    loop, registered = mock_loop

    async def run_and_trigger_stop(transport_name: str | None = None) -> None:
        callback = registered[signal.SIGTERM]
        callback()

    mock_worker.run.side_effect = run_and_trigger_stop

    with (
        patch.object(command, "argument", return_value=None),
        patch.object(asyncio, "get_running_loop", return_value=loop),
    ):
        await command.handle(mock_worker)

    # After the shutdown callback, signal handlers should be removed
    assert signal.SIGINT not in registered
    assert signal.SIGTERM not in registered
