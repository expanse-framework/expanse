from collections import defaultdict
from typing import overload

from expanse.types.messenger import Message
from expanse.types.messenger import Stamp
from expanse.types.messenger import StampT


class Envelope:
    def __init__(self, message: Message, stamps: list[Stamp] | None = None):
        self._message: Message = message
        self._stamps: dict[type[Stamp], list[Stamp]] = defaultdict(list)

        if stamps:
            for stamp in stamps:
                self._stamps[stamp.__class__].append(stamp)

    @classmethod
    def wrap(
        cls, message: "Message | Envelope", stamps: list[Stamp] | None = None
    ) -> "Envelope":
        if isinstance(message, Envelope):
            return message

        return cls(message, stamps)

    def open(self) -> Message:
        return self._message

    def with_stamps(self, *stamps: Stamp) -> "Envelope":
        """
        Add one or more stamps to the envelope.

        :param stamps: The stamps to add to the envelope.
        :return: A new envelope with the added stamps.
        """
        return self.__class__(self._message, stamps=[*self.stamps(), *stamps])

    def stamp(self, stamp_type: type[StampT]) -> StampT | None:
        """
        Get the last stamp of the given type from the envelope.

        :param stamp_type: The type of the stamp to retrieve.
        """
        stamps = self._stamps.get(stamp_type)

        if not stamps:
            return None

        return stamps[-1]

    def has_stamp(self, stamp_type: type[Stamp]) -> bool:
        """
        Check if the envelope has a stamp of the given type.

        :param stamp_type: The type of the stamp to check for.
        """
        return stamp_type in self._stamps

    def is_stamped(self) -> bool:
        """
        Check if the envelope has any stamps.

        :return: True if the envelope has at least one stamp, False otherwise.
        """
        return bool(self._stamps)

    def without_stamps(self, *stamp_types: type[Stamp]) -> "Envelope":
        """
        Remove all stamps of the given types from the envelope.

        :param stamp_types: The types of the stamps to remove from the envelope.
        :return: A new envelope without the specified stamps.
        """
        return self.__class__(
            self._message,
            stamps=[
                s for t, ls in self._stamps.items() for s in ls if t not in stamp_types
            ],
        )

    @overload
    def stamps(self, stamp_type: type[StampT]) -> list[StampT]: ...

    @overload
    def stamps(self, stamp_type: None = None) -> list[Stamp]: ...

    def stamps(self, stamp_type: type[StampT] | None = None) -> list[StampT]:
        """
        Get all stamps from the envelope, optionally filtered by type.

        :param stamp_type: The type of the stamps to retrieve. If None, return all stamps.
        :return: A list of stamps.
        """
        if stamp_type is not None:
            return self._stamps.get(stamp_type, [])

        return [s for ls in self._stamps.values() for s in ls]
