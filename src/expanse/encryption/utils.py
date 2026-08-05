import secrets


_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@$%&*-_+"
_RESTRICTED_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def generate_random_string(size: int = 32, restricted: bool = False) -> str:
    alphabet = _ALPHABET if not restricted else _RESTRICTED_ALPHABET

    return "".join(secrets.choice(alphabet) for _ in range(size))
