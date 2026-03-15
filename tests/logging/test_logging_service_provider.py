from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.logging.channel import LogChannel
from expanse.logging.logger import Logger
from expanse.logging.logging_manager import LoggingManager


if TYPE_CHECKING:
    from expanse.core.application import Application


async def test_logging_manager_is_resolved_from_container(
    app: Application,
) -> None:
    manager = await app.container.get(LoggingManager)

    assert isinstance(manager, LoggingManager)


async def test_logging_manager_is_singleton(app: Application) -> None:
    manager1 = await app.container.get(LoggingManager)
    manager2 = await app.container.get(LoggingManager)

    assert manager1 is manager2


async def test_logger_is_resolved_from_container(app: Application) -> None:
    logger = await app.container.get(Logger)

    assert isinstance(logger, Logger)


async def test_log_channel_is_resolved_from_container(app: Application) -> None:
    channel = await app.container.get(LogChannel)

    assert isinstance(channel, LogChannel)
