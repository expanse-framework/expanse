from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast
from typing import override

from asgiref.sync import async_to_sync
from sqlalchemy import event
from sqlalchemy.exc import MissingGreenlet
from sqlalchemy.util import await_only

from expanse.contracts.messenger.asynchronous.message_bus import (
    MessageBus as MessageBusContract,
)
from expanse.database.asynchronous.session import AsyncSession
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import TransactionalMessageBusError


if TYPE_CHECKING:
    from sqlalchemy.orm import SessionTransaction

    from expanse.database.synchronous.session import Session
    from expanse.types.messenger import Message


class TransactionalMessageBus(MessageBusContract):
    """
    A specialized message bus that queues messages until attached sessions are committed.
    Upon dispatch of a message, if no session is currently attached, the message is dispatched immediately
    through the decorated bus.

    If the attached session is rolled back, the message queue is cleared without dispatching any messages.

    Note that it properly handles nested transactions by creating a message queue for each transaction level.
    """

    def __init__(
        self,
        decorated_bus: MessageBusContract,
        session: Session | AsyncSession | None = None,
    ):
        self._decorated_bus: MessageBusContract = decorated_bus
        self._queued_messages: list[list[Envelope]] = []
        self._session: Session | None = None

        if session is not None:
            self.attach_session(session)

    def attach_session(self, session: Session | AsyncSession) -> None:
        if isinstance(session, AsyncSession):
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

        if session.in_transaction():
            self._queued_messages.append([])

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

    @override
    async def dispatch(self, message: Message | Envelope) -> Envelope:
        if not self._queued_messages:
            # If no transaction is currently active, dispatch the message directly through the decorated bus.
            return await self._decorated_bus.dispatch(message)

        envelope = Envelope.wrap(message)

        self._queued_messages[-1].append(envelope)

        return envelope

    def _dispatch_after_commit(self, session: Session) -> None:
        if not self._queued_messages:
            return

        current_queue = self._queued_messages[-1]

        # When a nested transaction is committed, merge its message queue with the parent transaction's queue instead of dispatching messages immediately.
        if len(self._queued_messages) > 1:
            parent_queue = self._queued_messages[-2]

            parent_queue.extend(current_queue)
            current_queue.clear()
            return

        for message in current_queue:
            try:
                await_only(self._decorated_bus.dispatch(message))
            except MissingGreenlet:
                # Not in a SQLAlchemy greenlet context (e.g., plain thread).
                # Schedule the coroutine on the captured event loop.
                async_to_sync(self._decorated_bus.dispatch)(message)

        current_queue.clear()

    def has_attached_session(self) -> bool:
        return self._session is not None

    def close(self) -> None:
        self.detach_session()

    def _append_new_message_queue(
        self, session: Session, transaction: SessionTransaction
    ) -> None:
        self._queued_messages.append([])

    def _pop_last_message_queue(
        self, session: Session, transaction: SessionTransaction
    ) -> None:
        if not self._queued_messages:
            self._last_message_queue = None
            return

        # If the transaction has ended and there are no more active transactions,
        # clear this transaction's queue. If there were still messages in the queue,
        # they will be discarded since it means the transaction was never committed
        # or rolled back.
        self._queued_messages.pop()
