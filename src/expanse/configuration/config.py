from typing import Any

from expanse.support.deep_mutable_mapping import DeepMutableMapping


class Config(DeepMutableMapping[Any]):
    def __init__(self, config: dict) -> None:
        super().__init__(**config)

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}({self._data!r})"
