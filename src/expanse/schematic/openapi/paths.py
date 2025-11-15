from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from expanse.schematic.openapi.path_item import PathItem
    from expanse.schematic.openapi.reference import Reference


class Paths:
    """
    Holds the relative paths to the individual endpoints and their operations.

    The path is appended to the URL from the Server Object in order to construct the full URL.
    """

    def __init__(self) -> None:
        self.paths: dict[str, PathItem | Reference] = {}

    def add_path(self, path: str, path_item: PathItem | Reference) -> Paths:
        if not path.startswith("/"):
            raise ValueError("Path must begin with a forward slash (/)")

        self.paths[path] = path_item
        return self

    def get_path(self, path: str) -> PathItem | Reference | None:
        return self.paths.get(path)

    def remove_path(self, path: str) -> Paths:
        self.paths.pop(path, None)
        return self

    def get_all_paths(self) -> dict[str, PathItem | Reference]:
        return self.paths.copy()

    def to_dict(self) -> dict[str, Any]:
        return {path: path_item.to_dict() for path, path_item in self.paths.items()}

    def __len__(self) -> int:
        return len(self.paths)

    def __contains__(self, path: str) -> bool:
        return path in self.paths

    def __iter__(self):
        return iter(self.paths)
