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
    """

    def __init__(
        self,
        decorated_bus: MessageBusContract,
        session: Session | AsyncSession | None = None,
    ):
        self._decorated_bus: MessageBusContract = decorated_bus
        self._queued_messages: list[Message | Envelope] = []
        self._has_attached_session: bool = False

        if session is not None:
            self.attach_session(session)

    def attach_session(self, session: Session | AsyncSession) -> None:
        self._has_attached_session = True

        if isinstance(session, AsyncSession):
            session = cast("Session", session.sync_session)

        # Register an after commit hook to dispatch messages after the transaction is committed.
        event.listen(session, "after_commit", self._dispatch_after_commit)

        # Register an after rollback hook to clear the message queue if the transaction is rolled back.
        # after_soft_rollback only fires when a transaction is active, so we also
        # wrap the session's rollback method to handle the case where rollback is
        # called without an active transaction (autobegin hasn't started).
        event.listen(session, "after_soft_rollback", self._clear_queue_after_rollback)

        original_rollback = session.rollback

        def _rollback_with_queue_clear() -> None:
            self._queued_messages.clear()
            original_rollback()

        session.rollback = _rollback_with_queue_clear  # type: ignore[method-assign]

    @override
    async def dispatch(self, message: Message | Envelope) -> Envelope:
        if not self._has_attached_session:
            # If no session is currently attached, dispatch the message directly through the decorated bus.
            return await self._decorated_bus.dispatch(message)

        envelope = Envelope.wrap(message)

        self._queued_messages.append(envelope)

        return envelope

    def _dispatch_after_commit(self, session: Session) -> None:
        messages = self._queued_messages.copy()

        self._queued_messages.clear()

        for message in messages:
            try:
                await_only(self._decorated_bus.dispatch(message))
            except MissingGreenlet:
                # Not in a SQLAlchemy greenlet context (e.g., plain thread).
                # Schedule the coroutine on the captured event loop.
                async_to_sync(self._decorated_bus.dispatch)(message)

    def _clear_queue_after_rollback(
        self, session: Session, previous_transaction: SessionTransaction
    ) -> None:
        self._queued_messages.clear()
