from __future__ import annotations

from pathlib import Path


class ViewFinder:
    def __init__(self, paths: list[Path]) -> None:
        self._paths: list[Path] = paths

    def add_paths(self, paths: list[Path]) -> None:
        self._paths.extend(paths)

    def find(self, view: str) -> str | None:
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
                    return path.joinpath(candidate).read_text()

        return None
