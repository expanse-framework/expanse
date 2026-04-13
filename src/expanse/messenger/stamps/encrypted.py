from dataclasses import dataclass


@dataclass(frozen=True)
class EncryptedStamp:
    """
    A stamp used to mark messages as encrypted.
    """

    label: str
