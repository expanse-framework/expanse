from __future__ import annotations

import os

from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable


class ViewFinder:
    def __init__(self, paths: list[Path]) -> None:
        self._paths: list[Path] = paths

    def add_paths(self, paths: list[Path]) -> None:
        self._paths.extend(paths)

    def find(self, view: str) -> tuple[str, str, Callable[[], bool]] | None:
        view_path = Path(view)

        if not view_path.suffix:
            candidates = [
                view_path.with_suffix(".jinja2"),
                view_path.with_suffix(".html.jinja2"),
                view_path.with_suffix(".html"),
            ]
        else:
            candidates = [view_path]

        for path in self._paths:
            for candidate in candidates:
                if path.joinpath(candidate).exists():
                    return self._source(path.joinpath(candidate))

        return None

    def _source(self, view: Path) -> tuple[str, str, Callable[[], bool]]:
        mtime = os.path.getmtime(view)

        def uptodate() -> bool:
            try:
                return os.path.getmtime(view) == mtime
            except OSError:
                return False

        return view.read_text(), view.as_posix(), uptodate
