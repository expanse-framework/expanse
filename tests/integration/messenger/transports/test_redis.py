from __future__ import annotations

import asyncio
import os

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from expanse.configuration.config import Config
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import UnrecoverableMessageHandlingError
from expanse.messenger.serializer import Serializer
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.transports.redis.config import RedisTransportConfig
from expanse.messenger.transports.redis.transport import RedisTransport
from expanse.redis.asynchronous.redis_manager import RedisManager


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from expanse.redis.asynchronous.connections.connection import (
        Connection as RedisConnection,
    )


pytestmark = pytest.mark.redis

REDIS_URL = f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/15"
STREAM = "test_messages"


@dataclass
class RedisMessage:
    value: str


@pytest.fixture()
async def redis_connection() -> AsyncGenerator[RedisConnection]:
    config = Config({"redis": {"connections": {"default": {"url": REDIS_URL}}}})
    manager = RedisManager(config)

    try:
        connection = await manager.connection()

        # Clean up any leftover state from a previous run
        await connection.delete(STREAM)
        await connection.delete(f"{STREAM}__queue")

        yield connection
    finally:
        await manager.close()


@pytest.fixture()
async def redis_transport(redis_connection: RedisConnection) -> RedisTransport:
    transport_config = RedisTransportConfig(
        stream=STREAM,
        group="test_group",
        consumer="test_consumer",
    )
    return RedisTransport(redis_connection, transport_config, Serializer())


async def test_transport_can_send_a_message(
    redis_transport: RedisTransport,
) -> None:
    envelope = Envelope.wrap(RedisMessage(value="hello"))
    result = await redis_transport.send(envelope)

    stamp = result.stamp(TransportMessageIdStamp)
    assert stamp is not None
    assert stamp.id is not None


async def test_transport_can_receive_a_message(
    redis_transport: RedisTransport,
) -> None:
    message = RedisMessage(value="receive-me")
    await redis_transport.send(Envelope.wrap(message))

    envelopes = [e async for e in redis_transport.receive()]

    assert len(envelopes) == 1
    received = envelopes[0]
    assert isinstance(received.open(), RedisMessage)
    assert received.open().value == message.value

    stamp = received.stamp(TransportMessageIdStamp)
    assert stamp is not None


async def test_transport_does_not_receive_delayed_messages(
    redis_transport: RedisTransport,
) -> None:
    delayed_envelope = Envelope.wrap(RedisMessage(value="delayed")).with_stamps(
        DelayStamp(delay=60_000)
    )
    await redis_transport.send(delayed_envelope)

    received = [e async for e in redis_transport.receive()]

    assert received == []


async def test_transport_can_acknowledge_a_message(
    redis_transport: RedisTransport,
) -> None:
    await redis_transport.send(Envelope.wrap(RedisMessage(value="ack-me")))

    envelopes = [e async for e in redis_transport.receive()]
    assert len(envelopes) == 1

    await redis_transport.acknowledge(envelopes[0])

    # After acknowledgment with delete_after_ack=True, the stream should be empty
    envelopes_after = [e async for e in redis_transport.receive()]
    assert envelopes_after == []


async def test_transport_can_reject_a_message(
    redis_transport: RedisTransport,
) -> None:
    await redis_transport.send(Envelope.wrap(RedisMessage(value="reject-me")))

    envelopes = [e async for e in redis_transport.receive()]
    assert len(envelopes) == 1

    await redis_transport.reject(envelopes[0])

    # After rejection with delete_after_reject=True, the stream should be empty
    envelopes_after = [e async for e in redis_transport.receive()]
    assert envelopes_after == []


async def test_acknowledge_raises_without_transport_message_id_stamp(
    redis_transport: RedisTransport,
) -> None:
    envelope = Envelope.wrap(RedisMessage(value="no-stamp"))

    with pytest.raises(UnrecoverableMessageHandlingError):
        await redis_transport.acknowledge(envelope)


async def test_reject_raises_without_transport_message_id_stamp(
    redis_transport: RedisTransport,
) -> None:
    envelope = Envelope.wrap(RedisMessage(value="no-stamp"))

    with pytest.raises(UnrecoverableMessageHandlingError):
        await redis_transport.reject(envelope)


async def test_consumer_skips_its_own_pending_messages_and_receives_new_ones(
    redis_connection: RedisConnection,
) -> None:
    transport = RedisTransport(
        redis_connection,
        RedisTransportConfig(
            stream=STREAM,
            group="test_group",
            consumer="consumer_a",
        ),
        Serializer(),
    )

    await transport.send(Envelope.wrap(RedisMessage(value="pending")))

    # First receive: message is delivered but NOT acknowledged — it stays pending
    first_batch = [e async for e in transport.receive()]
    assert len(first_batch) == 1
    assert first_batch[0].open().value == "pending"

    await transport.send(Envelope.wrap(RedisMessage(value="new")))

    # Second receive: consumer_a's own pending message is skipped
    # (the implementation treats it as currently in-flight by this consumer);
    # the newly queued message is returned instead.
    second_batch = [e async for e in transport.receive()]
    assert len(second_batch) == 1
    assert second_batch[0].open().value == "new"


async def test_unacknowledged_message_is_claimed_by_another_consumer(
    redis_connection: RedisConnection,
) -> None:
    consumer_a = RedisTransport(
        redis_connection,
        RedisTransportConfig(
            stream=STREAM,
            group="test_group",
            consumer="consumer_a",
        ),
        Serializer(),
    )
    # Consumer B uses idle_time=0 so it can immediately claim consumer A's pending messages
    consumer_b = RedisTransport(
        redis_connection,
        RedisTransportConfig(
            stream=STREAM,
            group="test_group",
            consumer="consumer_b",
            idle_time=0,
        ),
        Serializer(),
    )

    await consumer_a.send(Envelope.wrap(RedisMessage(value="pending")))

    # Consumer A receives but does NOT acknowledge
    first_batch = [e async for e in consumer_a.receive()]
    assert len(first_batch) == 1

    # Consumer B claims consumer A's idle pending message and redelivers it
    second_batch = [e async for e in consumer_b.receive()]
    assert len(second_batch) == 1
    assert second_batch[0].open().value == "pending"


async def test_delayed_message_is_received_after_its_delay_expires(
    redis_transport: RedisTransport,
) -> None:
    delayed_envelope = Envelope.wrap(RedisMessage(value="delayed")).with_stamps(
        DelayStamp(delay=200)  # 200ms
    )
    await redis_transport.send(delayed_envelope)

    # Message is not yet available
    before = [e async for e in redis_transport.receive()]
    assert before == []

    await asyncio.sleep(0.3)  # wait for the 200ms delay to expire

    after = [e async for e in redis_transport.receive()]
    assert len(after) == 1
    assert after[0].open().value == "delayed"


async def test_only_expired_delayed_messages_are_moved_to_the_stream(
    redis_transport: RedisTransport,
) -> None:
    await redis_transport.send(
        Envelope.wrap(RedisMessage(value="soon")).with_stamps(DelayStamp(delay=200))
    )
    await redis_transport.send(
        Envelope.wrap(RedisMessage(value="later")).with_stamps(DelayStamp(delay=60_000))
    )

    await asyncio.sleep(0.3)  # only the 200ms message is due

    received = [e async for e in redis_transport.receive()]
    assert len(received) == 1
    assert received[0].open().value == "soon"
