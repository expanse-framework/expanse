import logging

from collections.abc import Awaitable
from collections.abc import Callable

from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.outbox import OutboxStamp
from expanse.messenger.stamps.received import ReceivedStamp
from expanse.messenger.stamps.relayed import RelayedStamp
from expanse.messenger.transports.transport_manager import TransportManager


logger = logging.getLogger(__name__)


class RelayMessages:
    """
    Middleware that relays messages received from an outbox to their target transport.

    It is meant to be the last middleware of the stack so that it is the first one
    to process received messages: relayed messages are sent as-is to their target
    transport, where they will be handled, and the rest of the stack is skipped.
    """

    def __init__(self, transport_manager: TransportManager) -> None:
        self._transport_manager: TransportManager = transport_manager

    async def handle(
        self, envelope: Envelope, next_call: Callable[[Envelope], Awaitable[Envelope]]
    ) -> Envelope:
        received_stamp = envelope.stamp(ReceivedStamp)
        if received_stamp is None:
            return await next_call(envelope)

        outbox_stamp = envelope.stamp(OutboxStamp)
        if outbox_stamp is None:
            return await next_call(envelope)

        target_transport_name = outbox_stamp.target_transport_name
        if target_transport_name == received_stamp.transport_name:
            return await next_call(envelope)

        logger.debug(
            "Relaying outbox message %s to target transport '%s' from transport '%s'",
            type(envelope.open()).__name__,
            target_transport_name,
            received_stamp.transport_name,
        )

        target_transport = await self._transport_manager.transport(
            target_transport_name
        )

        await target_transport.send(envelope.without_stamps(ReceivedStamp))

        return envelope.with_stamps(
            RelayedStamp(target_transport_name=target_transport_name)
        )
