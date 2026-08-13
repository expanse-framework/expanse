from typing import Any
from typing import Self

from expanse.support._utils import class_to_name


class TrustedCollection:
    def __init__(self, classes: list[type[Any]] | None = None) -> None:
        self._classes: set[type[Any]] = set()
        self._class_names: set[str] = set()

        for cls in self.get_default_classes():
            self.trust(cls)

        if classes is not None:
            for cls in classes:
                self.trust(cls)

    @property
    def classes(self):
        return self._classes

    @property
    def class_names(self):
        return self._class_names

    def trust(self, *klass: type[Any]) -> Self:
        for k in klass:
            self._classes.add(k)
            self._class_names.add(class_to_name(k))

        return self

    def distrust(self, klass: type[Any]) -> Self:
        self._classes.remove(klass)
        self._class_names.remove(class_to_name(klass))

        return self

    def is_trusted(self, klass: type[Any]) -> bool:
        return klass in self._classes

    def is_trusted_name(self, class_name: str) -> bool:
        return class_name in self._class_names

    def get_default_classes(self) -> set[type[Any]]:
        from expanse.jobs.stamps.job import JobStamp
        from expanse.messenger.exceptions import MessageDecodingFailedError
        from expanse.messenger.stamps.context import ContextStamp
        from expanse.messenger.stamps.delay import DelayStamp
        from expanse.messenger.stamps.encrypted import EncryptedStamp
        from expanse.messenger.stamps.handled import HandledStamp
        from expanse.messenger.stamps.received import ReceivedStamp
        from expanse.messenger.stamps.redelivery import RedeliveryStamp
        from expanse.messenger.stamps.sensitive import SensitiveStamp
        from expanse.messenger.stamps.sent_to_failure_transport import (
            SentToFailureTransportStamp,
        )
        from expanse.messenger.stamps.transport import TransportStamp
        from expanse.messenger.stamps.transport_message_id import (
            TransportMessageIdStamp,
        )
        from expanse.messenger.stamps.unique import UniqueStamp

        return {
            ContextStamp,
            DelayStamp,
            EncryptedStamp,
            HandledStamp,
            JobStamp,
            ReceivedStamp,
            RedeliveryStamp,
            SensitiveStamp,
            SentToFailureTransportStamp,
            TransportStamp,
            TransportMessageIdStamp,
            UniqueStamp,
            # MessageDecodingFailedError is also trusted by default, as it is used to wrap decoding errors in an envelope
            # and is not a message type that can be instantiated from untrusted data.
            MessageDecodingFailedError,
        }
