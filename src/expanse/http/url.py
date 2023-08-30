from __future__ import annotations

from starlette.datastructures import URL as BaseURL  # noqa: N811

from expanse.support._utils import string_matches


class URL(BaseURL):
    def is_(self, pattern: str | list[str]) -> bool:
        """
        Determine if the full URL matches a given pattern.
        """
        return string_matches(self._url, pattern)

    def path_is(self, pattern: str | list[str]) -> bool:
        """
        Determine if the full URL matches a given pattern.
        """
        return string_matches(self.path.lstrip("/"), pattern)
