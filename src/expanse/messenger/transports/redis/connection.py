import base64
import json
import secrets
import time

from collections.abc import AsyncIterator
from typing import Any

from redis.exceptions import ResponseError

from expanse.messenger.exceptions import TransportError
from expanse.messenger.transports.redis.config import RedisTransportConfig
from expanse.redis.asynchronous.connections.connection import (
    Connection as RedisConnection,
)


class Connection:
    def __init__(
        self, connection: RedisConnection, config: RedisTransportConfig
    ) -> None:
        self._connection: RedisConnection = connection
        self._config: RedisTransportConfig = config
        self._queue: str = f"{self._config.stream}__queue"
        self._last_pending_message_id: str | None = None

    async def add(self, body: str, headers: dict[str, Any], delay: int = 0) -> str:
        """
        Add a message to the Redis stream.

        :param body: The message body to be stored.
        :param headers: The message headers to be stored.
        :param delay: The number of milliseconds to delay the message before it becomes available for processing.
        """
        if self._config.auto_setup:
            await self.setup()

        if delay > 0:
            id = base64.b64encode(secrets.token_bytes(9)).decode()
            now = time.time() * 1000
            score = now + delay
            added = await self._connection.zadd(
                self._queue,
                {json.dumps({"body": body, "headers": headers, "uid": id}): score},
                nx=True,
            )
        else:
            message = json.dumps({"body": body, "headers": headers})
            id = added = await self._connection.xadd(
                self._config.stream,
                fields={"message": message},
                maxlen=self._config.max_entries,
                approximate=True,
            )

        if not added:
            raise RuntimeError("Failed to add message to Redis stream")

        return id

    async def get(self, count: int = 1) -> AsyncIterator[dict[str, Any]]:
        """
        Get messages from the Redis stream.

        :return: A list of messages, or None if there are no messages available.
        """
        if self._config.auto_setup:
            await self.setup()

        await self._handle_delayed_messages()

        retrieved: int = 0

        if retrieved < count:
            async for message in self._get_pending_messages():
                yield message
                retrieved += 1

        if retrieved < count:
            await self._claim_old_pending_messages()

            async for message in self._get_pending_messages():
                yield message
                retrieved += 1

        if retrieved < count:
            async for message in self._get_new_messages():
                yield message
                retrieved += 1

    async def acknowledge(self, message_id: str) -> None:
        is_acknowledged = await self._connection.xack(
            self._config.stream, self._config.group, message_id
        )

        if self._config.delete_after_ack:
            await self._connection.xdel(self._config.stream, message_id)

        if not is_acknowledged:
            raise TransportError(f"Failed to acknowledge message with ID {message_id}")

    async def reject(self, message_id: str) -> None:
        is_rejected = await self._connection.xack(
            self._config.stream, self._config.group, message_id
        )

        if self._config.delete_after_reject:
            await self._connection.xdel(self._config.stream, message_id)

        if not is_rejected:
            raise TransportError(f"Failed to acknowledge message with ID {message_id}")

    async def setup(self) -> None:
        try:
            await self._connection.xgroup_create(
                self._config.stream, self._config.group, 0, mkstream=True
            )
        except ResponseError as e:
            if "BUSYGROUP" in str(e):
                # The group already exists, which is fine, we just ignore the error.
                pass
            else:
                raise

    async def _handle_delayed_messages(self) -> None:
        now = time.time() * 1000
        message_count = await self._connection.zcount(self._queue, 0, now) or 0

        while message_count > 0:
            message_count -= 1
            message_info = await self._connection.zpopmin(self._queue, count=1)

            if not message_info:
                break

            message, score = message_info[0]

            if score > now:
                # If the message is not yet due, we put it back in the sorted set and break the loop to wait for the next check.
                try:
                    await self._connection.zadd(self._queue, {message: score}, nx=True)
                except Exception as e:
                    raise TransportError(
                        f"Failed to re-add delayed message to Redis sorted set: {e}"
                    )

                break

            try:
                data = json.loads(message)
                body = data["body"]
                headers = data["headers"]
            except (json.JSONDecodeError, KeyError):
                # If the message is not in the expected format, we skip it and remove it from the sorted set to prevent it from blocking other messages.
                await self._connection.zrem(self._queue, message)
                continue

            try:
                await self.add(body, headers)
            except Exception as e:
                raise TransportError(
                    f"Failed to add delayed message to Redis stream: {e}"
                )

    async def _get_new_messages(self) -> AsyncIterator[dict[str, Any]]:
        for message in await self._connection.xreadgroup(
            self._config.group,
            self._config.consumer,
            streams={self._config.stream: ">"},
            count=1,
            block=1000,
        ):
            yield {
                "id": message[1][0][0],
                "data": message[1][0][1]["message"],
            }

    async def _get_pending_messages(self) -> AsyncIterator[dict[str, Any]]:
        if self._last_pending_message_id is None:
            return

        while True:
            messages = await self._connection.xreadgroup(
                self._config.group,
                self._config.consumer,
                streams={self._config.stream: self._last_pending_message_id},
                count=1,
                block=1000,
            )

            if not messages:
                return

            for _stream, entries in messages:
                for message_id, fields in entries:
                    self._last_pending_message_id = message_id
                    yield {"id": message_id, "data": fields["message"]}

    async def _claim_old_pending_messages(self) -> None:
        try:
            pending = await self._connection.xpending_range(
                self._config.stream, self._config.group, "-", "+", 1
            )
        except Exception as e:
            raise TransportError(
                f"Failed to retrieve pending messages from Redis stream: {e}"
            )

        if not pending:
            return

        try:
            await self._connection.xclaim(
                self._config.stream,
                self._config.group,
                self._config.consumer,
                min_idle_time=self._config.idle_time * 1000,
                message_ids=[pending[0]["message_id"]],
                justid=True,
            )
        except Exception as e:
            raise TransportError(
                f"Failed to claim pending message with ID {pending[0]['message_id']}: {e}"
            )

        self._last_pending_message_id = "0"
