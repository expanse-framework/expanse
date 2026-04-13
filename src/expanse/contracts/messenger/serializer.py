from abc import ABC
from abc import abstractmethod

from expanse.messenger.envelope import Envelope
from expanse.types.messenger import EncodedEnvelope


class Serializer(ABC):
    @abstractmethod
    def encode(self, envelope: Envelope) -> EncodedEnvelope:
        """
        Encode an envelope into a format suitable for transport.

        :param envelope: The envelope to encode.
        :return: The encoded envelope.
        """
        ...

    @abstractmethod
    def decode(self, encoded_envelope: EncodedEnvelope) -> Envelope:
        """
        Decode an encoded envelope back into an Envelope object.

        :param encoded_envelope: The encoded envelope to decode.
        :return: The decoded Envelope object.
        """
        ...
