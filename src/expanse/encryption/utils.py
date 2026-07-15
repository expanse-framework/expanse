import secrets


_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@$%&*-_+"


def generate_random_string(size: int = 32) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(size))
