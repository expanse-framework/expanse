from __future__ import annotations

import asyncio
import contextlib
import os

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from expanse.cache.asynchronous.buses.redis import RedisBus
from expanse.redis.asynchronous.redis_manager import RedisManager


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from expanse.core.application import Application


pytestmark = pytest.mark.redis


@dataclass
class Ping:
    data: str = ""


@dataclass
class Pong:
    data: str = ""


@pytest.fixture(autouse=True)
async def setup_redis(app: Application) -> AsyncGenerator[None]:
    from expanse.redis.redis_service_provider import RedisServiceProvider

    app.config["redis"] = {
        "connection": "default",
        "connections": {
            "default": {
                "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/3"
            }
        },
    }

    await RedisServiceProvider(app.container).register()

    yield

    manager = await app.container.get(RedisManager)
    connection = manager.connection("default")
    await connection.flushdb()


@pytest.fixture()
async def redis(app: Application) -> RedisManager:
    return await app.container.get(RedisManager)


@pytest.fixture()
async def bus_a(redis: RedisManager) -> AsyncGenerator[RedisBus]:
    publisher = redis.create_connection("default")
    subscriber = redis.create_connection("default")
    bus = RedisBus(publisher, subscriber, "cache-bus-async-test")
    await asyncio.sleep(0.05)
    yield bus
    await bus.close()
    await asyncio.sleep(0.05)
    await publisher.aclose()
    await subscriber.aclose()


@pytest.fixture()
async def bus_b(redis: RedisManager) -> AsyncGenerator[RedisBus]:
    publisher = redis.create_connection("default")
    subscriber = redis.create_connection("default")
    bus = RedisBus(publisher, subscriber, "cache-bus-async-test")
    await asyncio.sleep(0.05)
    yield bus
    await bus.close()
    await asyncio.sleep(0.05)
    await publisher.aclose()
    await subscriber.aclose()


async def test_id_is_a_unique_string(bus_a: RedisBus, bus_b: RedisBus) -> None:
    assert isinstance(bus_a.id, str)
    assert len(bus_a.id) > 0
    assert bus_a.id != bus_b.id


async def test_publish_delivers_message_to_another_bus(
    bus_a: RedisBus, bus_b: RedisBus
) -> None:
    received: asyncio.Event = asyncio.Event()
    captured: list[Ping] = []

    def handler(msg: Ping) -> None:
        captured.append(msg)
        received.set()

    bus_b.subscribe(Ping, handler)
    await bus_a.publish(Ping("hello"))

    await asyncio.wait_for(received.wait(), timeout=2.0)
    assert captured == [Ping("hello")]


async def test_publish_does_not_deliver_to_same_bus(
    bus_a: RedisBus, bus_b: RedisBus
) -> None:
    a_received: asyncio.Event = asyncio.Event()
    b_received: asyncio.Event = asyncio.Event()

    bus_a.subscribe(Ping, lambda _: a_received.set())
    bus_b.subscribe(Ping, lambda _: b_received.set())

    await bus_a.publish(Ping("hello"))

    # Confirm message propagated through Redis by waiting for bus_b
    await asyncio.wait_for(b_received.wait(), timeout=2.0)
    # bus_a should have ignored its own message
    assert not a_received.is_set()


async def test_subscribe_only_delivers_matching_message_type(
    bus_a: RedisBus, bus_b: RedisBus
) -> None:
    ping_received: asyncio.Event = asyncio.Event()
    pong_received: asyncio.Event = asyncio.Event()

    bus_b.subscribe(Ping, lambda _: ping_received.set())
    bus_b.subscribe(Pong, lambda _: pong_received.set())

    await bus_a.publish(Ping("hello"))

    await asyncio.wait_for(ping_received.wait(), timeout=2.0)
    assert not pong_received.is_set()


async def test_multiple_handlers_are_all_invoked(
    bus_a: RedisBus, bus_b: RedisBus
) -> None:
    first: asyncio.Event = asyncio.Event()
    second: asyncio.Event = asyncio.Event()

    bus_b.subscribe(Ping, lambda _: first.set())
    bus_b.subscribe(Ping, lambda _: second.set())

    await bus_a.publish(Ping("hello"))

    await asyncio.wait_for(asyncio.gather(first.wait(), second.wait()), timeout=2.0)


async def test_async_handler_is_invoked(bus_a: RedisBus, bus_b: RedisBus) -> None:
    received: asyncio.Event = asyncio.Event()

    async def async_handler(msg: Ping) -> None:
        received.set()

    bus_b.subscribe(Ping, async_handler)
    await bus_a.publish(Ping("hello"))

    await asyncio.wait_for(received.wait(), timeout=2.0)


async def test_close_stops_message_delivery(
    bus_a: RedisBus, redis: RedisManager
) -> None:
    publisher = redis.create_connection("default")
    subscriber = redis.create_connection("default")
    bus_b = RedisBus(publisher, subscriber, "cache-bus-async-test")
    await asyncio.sleep(0.05)

    b_count = 0
    b_event: asyncio.Event = asyncio.Event()

    def b_handler(msg: Ping) -> None:
        nonlocal b_count
        b_count += 1
        b_event.set()

    bus_b.subscribe(Ping, b_handler)

    await bus_a.publish(Ping("before close"))
    await asyncio.wait_for(b_event.wait(), timeout=2.0)
    assert b_count == 1

    await bus_b.close()
    with contextlib.suppress(asyncio.CancelledError):
        await bus_b._listen_task
    b_event.clear()

    await bus_a.publish(Ping("after close"))
    await asyncio.sleep(0.2)
    assert b_count == 1

    await publisher.aclose()
    await subscriber.aclose()
