from dataclasses import dataclass


@dataclass
class HandledStamp:
    """
    Stamp to mark a message as handled.

    This stamp is added to the envelope after a handler has processed the message.
    """

    handler: str
