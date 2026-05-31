from __future__ import annotations

import asyncio
import os
import threading
import time

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from expanse.cache.synchronous.buses.redis import RedisBus
from expanse.redis.synchronous.redis_manager import RedisManager


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
                "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/4"
            }
        },
    }

    await RedisServiceProvider(app.container).register()

    yield

    manager = await app.container.get(RedisManager)
    connection = manager.connection("default")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, connection.flushdb)


@pytest.fixture()
async def redis(app: Application) -> RedisManager:
    return await app.container.get(RedisManager)


@pytest.fixture()
async def bus_a(redis: RedisManager) -> AsyncGenerator[RedisBus]:
    publisher = redis.create_connection("default")
    subscriber = redis.create_connection("default")
    bus = RedisBus(publisher, subscriber, "cache-bus-sync-test")
    await asyncio.sleep(0.05)
    yield bus
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, bus.close)
    publisher.close()
    subscriber.close()


@pytest.fixture()
async def bus_b(redis: RedisManager) -> AsyncGenerator[RedisBus]:
    publisher = redis.create_connection("default")
    subscriber = redis.create_connection("default")
    bus = RedisBus(publisher, subscriber, "cache-bus-sync-test")
    await asyncio.sleep(0.05)
    yield bus
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, bus.close)
    publisher.close()
    subscriber.close()


def test_id_is_a_unique_string(bus_a: RedisBus, bus_b: RedisBus) -> None:
    assert isinstance(bus_a.id, str)
    assert len(bus_a.id) > 0
    assert bus_a.id != bus_b.id


def test_publish_delivers_message_to_another_bus(
    bus_a: RedisBus, bus_b: RedisBus
) -> None:
    received = threading.Event()
    captured: list[Ping] = []

    def handler(msg: Ping) -> None:
        captured.append(msg)
        received.set()

    bus_b.subscribe(Ping, handler)
    bus_a.publish(Ping("hello"))

    assert received.wait(timeout=2.0), "Message not delivered within timeout"
    assert captured == [Ping("hello")]


def test_publish_does_not_deliver_to_same_bus(bus_a: RedisBus, bus_b: RedisBus) -> None:
    a_received = threading.Event()
    b_received = threading.Event()

    bus_a.subscribe(Ping, lambda _: a_received.set())
    bus_b.subscribe(Ping, lambda _: b_received.set())

    bus_a.publish(Ping("hello"))

    # Confirm message propagated through Redis by waiting for bus_b
    assert b_received.wait(timeout=2.0), "Control message not received"
    # bus_a should have ignored its own message
    assert not a_received.is_set()


def test_subscribe_only_delivers_matching_message_type(
    bus_a: RedisBus, bus_b: RedisBus
) -> None:
    ping_received = threading.Event()
    pong_received = threading.Event()

    bus_b.subscribe(Ping, lambda _: ping_received.set())
    bus_b.subscribe(Pong, lambda _: pong_received.set())

    bus_a.publish(Ping("hello"))

    assert ping_received.wait(timeout=2.0), "Ping not delivered"
    assert not pong_received.is_set()


def test_multiple_handlers_are_all_invoked(bus_a: RedisBus, bus_b: RedisBus) -> None:
    first = threading.Event()
    second = threading.Event()

    bus_b.subscribe(Ping, lambda _: first.set())
    bus_b.subscribe(Ping, lambda _: second.set())

    bus_a.publish(Ping("hello"))

    assert first.wait(timeout=2.0), "First handler not invoked"
    assert second.wait(timeout=2.0), "Second handler not invoked"


def test_close_stops_message_delivery(bus_a: RedisBus, redis: RedisManager) -> None:
    publisher = redis.create_connection("default")
    subscriber = redis.create_connection("default")
    bus_b = RedisBus(publisher, subscriber, "cache-bus-sync-test")
    time.sleep(0.05)

    b_count = 0
    b_event = threading.Event()

    def b_handler(msg: Ping) -> None:
        nonlocal b_count
        b_count += 1
        b_event.set()

    bus_b.subscribe(Ping, b_handler)

    bus_a.publish(Ping("before close"))
    assert b_event.wait(timeout=2.0), "Initial message not delivered"
    assert b_count == 1

    bus_b.close()
    b_event.clear()

    bus_a.publish(Ping("after close"))
    time.sleep(0.2)
    assert b_count == 1

    publisher.close()
    subscriber.close()
