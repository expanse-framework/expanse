from collections.abc import Iterator

from expanse.encryption.key import Key


class KeyChain:
    def __init__(self, keys: list[Key]):
        self._keys = keys

    @property
    def latest(self) -> Key:
        return self._keys[0]

    def add(self, key: Key):
        self._keys.append(key)

    def __iter__(self) -> Iterator[Key]:
        return iter(self._keys)

    def __len__(self) -> int:
        return len(self._keys)
