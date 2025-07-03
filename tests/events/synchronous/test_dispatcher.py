import logging

from typing import Literal

from pytest import LogCaptureFixture

from expanse.container.container import Container
from expanse.events.synchronous.dispatcher import EventDispatcher


logger = logging.getLogger(__name__)


class MyEvent: ...


class FooListener:
    async def handle(self, event: MyEvent) -> None:
        logger.info("FooListener called")


class SyncListener:
    def handle(self, event: MyEvent) -> None:
        logger.info("SyncListener called")


async def stopping_listener(self, event: MyEvent) -> Literal[False]:
    logger.info("stopping_listener called")

    return False  # This will stop the propagation of the event


def test_dispatcher_can_call_async_listener(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    dispatcher = EventDispatcher(Container())
    dispatcher.listen(MyEvent, FooListener)

    dispatcher.dispatch(MyEvent())

    assert "FooListener called" in caplog.messages


def test_dispatcher_can_call_sync_listener(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    dispatcher = EventDispatcher(Container())
    dispatcher.listen(MyEvent, SyncListener)

    dispatcher.dispatch(MyEvent())

    assert "SyncListener called" in caplog.messages


def test_dispatcher_stops_on_false_return(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    dispatcher = EventDispatcher(Container())
    dispatcher.listen(MyEvent, stopping_listener)
    dispatcher.listen(MyEvent, FooListener)  # This should not be called

    dispatcher.dispatch(MyEvent())

    assert "stopping_listener called" in caplog.messages
    assert "FooListener called" not in caplog.messages
