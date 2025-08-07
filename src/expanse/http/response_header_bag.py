from collections.abc import Mapping

from expanse.http.header_bag import HeaderBag


class ResponseHeaderBag(HeaderBag):
    __slots__ = ("_header_names",)

    def __init__(self, headers: Mapping[str, str] | None = None) -> None:
        self._header_names: dict[str, str] = {}

        super().__init__(headers or {})

    def set(
        self, name: str, value: str | list[str | None] | None, replace: bool = True
    ) -> None:
        normalized_name = self._normalize_name(name)
        self._header_names[normalized_name] = name

        super().set(name, value, replace)

    def encode(self) -> list[tuple[bytes, bytes]]:
        return [
            (
                self._header_names[name].encode("ascii"),
                ",".join(_ for _ in value if _ is not None).encode("latin-1"),
            )
            for name, value in self._headers.items()
        ]
