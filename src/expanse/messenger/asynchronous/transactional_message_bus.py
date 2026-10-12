from __future__ import annotations

import logging

from typing import TYPE_CHECKING
from typing import Any
from typing import cast
from typing import override

from asgiref.sync import async_to_sync
from sqlalchemy import event
from sqlalchemy.util import await_only
from sqlalchemy.util.concurrency import in_greenlet

from expanse.contracts.messenger.asynchronous.message_bus import (
    MessageBus as MessageBusContract,
)
from expanse.database.asynchronous.session import AsyncSession
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import TransactionalMessageBusError
from expanse.messenger.stamps.transport import TransportStamp
from expanse.messenger.stamps.unique_lock_acquired import UniqueLockAcquiredStamp
from expanse.messenger.transports.database.transport import DatabaseTransport
from expanse.messenger.transports.outbox.transport import OutboxTransport


if TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable

    from sqlalchemy.orm import SessionTransaction

    from expanse.container.container import Container
    from expanse.database.synchronous.session import Session
    from expanse.messenger.transports.transport_manager import TransportManager
    from expanse.types.messenger import Message


logger = logging.getLogger(__name__)


class TransactionalMessageBus(MessageBusContract):
    """
    A specialized message bus that queues messages until attached sessions are committed.
    Upon dispatch of a message, if no session is currently attached, the message is dispatched immediately
    through the decorated bus.

    If the attached session is rolled back, the message queue is cleared without dispatching any messages.

    Messages for transports with an outbox are stored in the outbox immediately when the outbox
    shares the connection of the attached session, so that they are part of its transaction.
    Otherwise, they are queued like any other message.

    Note that it properly handles nested transactions by creating a message queue for each transaction level.
    """

    def __init__(
        self,
        transport_manager: TransportManager,
        decorated_bus: MessageBusContract,
        session: Session | AsyncSession | None = None,
        container: Container | None = None,
    ):
        self._transport_manager: TransportManager = transport_manager
        self._decorated_bus: MessageBusContract = decorated_bus
        self._container: Container | None = container
        self._queued_messages: list[list[Envelope]] = []
        # Envelopes stored in the outbox, as part of each transaction level,
        # whose unique lock was acquired upon dispatch. Their locks must be released
        # if the transaction is rolled back, since they will never be handled.
        self._locked_outboxed_messages: list[list[Envelope]] = []
        self._session: Session | None = None
        self._async_session: AsyncSession | None = None

        if session is not None:
            self.attach_session(session)

    def attach_session(self, session: Session | AsyncSession) -> None:
        async_session: AsyncSession | None = None
        if isinstance(session, AsyncSession):
            async_session = session
            session = cast("Session", session.sync_session)

        if self._session is not None and self._session is not session:
            raise TransactionalMessageBusError(
                "A session is already attached to the transactional message bus."
                " Detach the current session before attaching a new one."
            )

        if self._session is session:
            # Session is already attached, no need to re-attach.
            return

        self._session = session
        self._async_session = async_session

        if session.in_transaction():
            self._append_new_message_queue(session, None)

        event.listen(
            session, "after_transaction_create", self._append_new_message_queue
        )
        event.listen(session, "after_transaction_end", self._pop_last_message_queue)

        # Register an after commit hook to dispatch messages after the transaction is committed.
        event.listen(session, "after_commit", self._dispatch_after_commit)

    def detach_session(self) -> None:
        if self._session is None:
            return

        event.remove(
            self._session, "after_transaction_create", self._append_new_message_queue
        )
        event.remove(
            self._session, "after_transaction_end", self._pop_last_message_queue
        )
        event.remove(self._session, "after_commit", self._dispatch_after_commit)

        self._session = None
        self._async_session = None

    @override
    async def dispatch(self, message: Message | Envelope) -> Envelope:
        if not self._queued_messages:
            # If no transaction is currently active, dispatch the message directly through the decorated bus.
            return await self._decorated_bus.dispatch(message)

        envelope = Envelope.wrap(message)

        transport_stamp = envelope.stamp(TransportStamp)
        transport_name = transport_stamp.name if transport_stamp else None
        transport = await self._transport_manager.transport(transport_name)

        if isinstance(
            transport, OutboxTransport
        ) and await self._joins_session_transaction(transport):
            # The outbox stores the message as part of the session's transaction,
            # so it can be dispatched right away.
            dispatched = await self._decorated_bus.dispatch(envelope)

            if dispatched.has_stamp(UniqueLockAcquiredStamp):
                self._locked_outboxed_messages[-1].append(envelope)

            return dispatched

        self._queued_messages[-1].append(envelope)

        return envelope

    async def _joins_session_transaction(self, transport: OutboxTransport) -> bool:
        """
        Whether messages stored in the outbox of the given transport
        are part of the transaction of the attached session.
        """
        if self._async_session is None:
            # Synchronous sessions never share their connection with the outbox.
            return False

        outbox = transport.outbox_transport
        if not isinstance(outbox, DatabaseTransport):
            return False

        if self._async_session.bind is not outbox.connection:
            return False

        # Sessions only begin their transaction on the connection upon their first
        # database operation. Ensure it is begun, otherwise the outbox would commit
        # the message on its own, regardless of the outcome of the transaction.
        await self._async_session.connection()

        return True

    def _dispatch_after_commit(self, session: Session) -> None:
        if not self._queued_messages:
            return

        current_queue = self._queued_messages[-1]
        current_locked_outboxed = self._locked_outboxed_messages[-1]

        # When a nested transaction is committed, merge its message queue with the parent transaction's queue instead of dispatching messages immediately.
        if len(self._queued_messages) > 1:
            parent_queue = self._queued_messages[-2]

            parent_queue.extend(current_queue)
            current_queue.clear()

            # Outboxed messages are now tied to the outcome of the parent transaction.
            self._locked_outboxed_messages[-2].extend(current_locked_outboxed)
            current_locked_outboxed.clear()

            return

        # Outboxed messages are committed: their locks will be released once handled.
        current_locked_outboxed.clear()

        for message in current_queue:
            self._run(self._decorated_bus.dispatch, message)

        current_queue.clear()

    def has_attached_session(self) -> bool:
        return self._session is not None

    def close(self) -> None:
        self.detach_session()

    def _append_new_message_queue(
        self, session: Session, transaction: SessionTransaction | None
    ) -> None:
        self._queued_messages.append([])
        self._locked_outboxed_messages.append([])

    def _pop_last_message_queue(
        self, session: Session, transaction: SessionTransaction
    ) -> None:
        if not self._queued_messages:
            return

        # If the transaction has ended and there are no more active transactions,
        # clear this transaction's queue. If there were still messages in the queue,
        # they will be discarded since it means the transaction was never committed
        # or rolled back.
        self._queued_messages.pop()

        # Committed transactions have already emptied this list, so any remaining
        # outboxed message has been rolled back along with its transaction.
        for envelope in self._locked_outboxed_messages.pop():
            self._run(self._release_unique_lock, envelope)

    async def _release_unique_lock(self, envelope: Envelope) -> None:
        from expanse.contracts.cache.asynchronous.cache import Cache
        from expanse.messenger.locks.unique import UniqueLock

        if self._container is None:
            logger.warning(
                "Unable to release the unique lock of a rolled back message: no container available.",
                extra={"message_type": type(envelope.open()).__name__},
            )

            return

        await UniqueLock(await self._container.get(Cache)).release(envelope)

    def _run(
        self, function: Callable[[Envelope], Awaitable[Any]], envelope: Envelope
    ) -> None:
        if in_greenlet():
            await_only(function(envelope))
        else:
            # Not in a SQLAlchemy greenlet context (e.g., plain thread).
            # Schedule the coroutine on the captured event loop.
            async_to_sync(function)(envelope)
