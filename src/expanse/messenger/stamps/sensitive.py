from dataclasses import dataclass


@dataclass
class SensitiveStamp:
    """
    A stamp to indicate that a message contains sensitive information.

    Messages marked with this stamp will be encrypted before being sent.
    """
