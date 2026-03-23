from expanse.types.messenger import Message
from expanse.types.messenger import Stamp
from expanse.types.messenger import StampT


class Envelope:
    def __init__(self, message: Message, stamps: list[Stamp] | None = None):
        self._message: Message = message
        self._stamps: dict[type[Stamp], Stamp] = {}

        if stamps:
            for stamp in stamps:
                self._stamps[stamp.__class__] = stamp

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
        return self.__class__(self._message, stamps=[*self.stamps, *stamps])

    def stamp(self, stamp_type: type[StampT]) -> StampT | None:
        """
        Get a stamp of the given type from the envelope.

        :param stamp_type: The type of the stamp to retrieve.
        """
        return self._stamps.get(stamp_type)

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

    @property
    def stamps(self) -> list[Stamp]:
        """
        Get all stamps from the envelope.

        :return: A list of all stamps in the envelope.
        """
        return list(self._stamps.values())
