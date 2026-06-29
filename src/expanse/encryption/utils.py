import secrets
import string


_ALPHABET = string.ascii_lowercase + string.ascii_uppercase + string.digits


def generate_random_string(size: int = 32) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(size))
