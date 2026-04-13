from typing import Literal

from expanse.messenger.transports.config import BaseTransportConfig


class RedisTransportConfig(BaseTransportConfig):
    driver: Literal["redis"] = "redis"

    # The redis connection to use
    connection: str | None = None

    # Name of the stream to retrieve messages from.
    stream: str = "messages"

    # Name of the consumer group to use for retrieving messages from the stream.
    group: str = "expanse"

    # Name of the consumer to use for retrieving messages from the stream.
    # This is used in combination with the group name to identify the consumer in the consumer group.
    # It should be unique for each instance of the messenger to avoid conflicts with other instances consuming from the same stream and group.
    consumer: str = "consumer"

    # Whether to automatically create the stream and consumer group if they do not exist.
    auto_setup: bool = True

    # Whether to automatically delete messages from the stream after they have been acknowledged.
    delete_after_ack: bool = True

    # Whether to automatically delete messages after they have been rejected.
    delete_after_reject: bool = True

    # The maximum number of entries which the stream will be trimmed to.
    # This is used to prevent the stream from growing indefinitely and consuming too much memory.
    # It is recommended to set this to a reasonable value based on the expected message volume and retention period.
    # Note that setting this to a low value may result in messages being deleted before they are processed, so it should be set with caution.
    max_entries: int | None = None

    # The maximum amount of time (in seconds) a message can be idle
    # (i.e: delivered but not acknowledged or rejected) before it is considered for redelivery.
    idle_time: int = 3600

    # The interval (in seconds) at which to check for idle messages and claim them for redelivery.
    claim_interval: int = 60
