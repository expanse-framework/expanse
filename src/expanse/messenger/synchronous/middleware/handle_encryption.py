from collections.abc import Callable

from expanse.messenger.envelope import Envelope
from expanse.messenger.middleware.handle_encryption import BaseHandleEncryption
from expanse.messenger.stamps.sensitive import SensitiveStamp


class HandleEncryption(BaseHandleEncryption):
    """
    Middleware to encrypt sensitive messages upon sending.
    """

    def handle(
        self, envelope: Envelope, next_call: Callable[[Envelope], Envelope]
    ) -> Envelope:
        if not envelope.has_stamp(SensitiveStamp):
            return next_call(envelope)

        return next_call(self._encrypt(envelope))
