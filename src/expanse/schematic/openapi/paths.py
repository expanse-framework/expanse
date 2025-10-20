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
    The Paths MAY be empty, due to Access Control List (ACL) constraints.
    """

    def __init__(self) -> None:
        """Initialize a Paths object."""
        self.paths: dict[str, PathItem | Reference] = {}

    def add_path(self, path: str, path_item: PathItem | Reference) -> Paths:
        """
        Add a path and its operations.

        Args:
            path: A relative path to an individual endpoint. The field name MUST begin
                 with a forward slash (/). The path is appended (no relative URL resolution)
                 to the expanded URL from the Server Object's url field in order to construct
                 the full URL. Path templating is allowed.
            path_item: A Path Item Object or Reference Object that describes the operations
                      available on this path.

        Returns:
            Self for method chaining

        Raises:
            ValueError: If the path does not start with a forward slash
        """
        if not path.startswith("/"):
            raise ValueError("Path must begin with a forward slash (/)")

        self.paths[path] = path_item
        return self

    def get_path(self, path: str) -> PathItem | Reference | None:
        """
        Get a path item by path.

        Args:
            path: The path to retrieve

        Returns:
            The PathItem or Reference if found, None otherwise
        """
        return self.paths.get(path)

    def remove_path(self, path: str) -> Paths:
        """
        Remove a path.

        Args:
            path: The path to remove

        Returns:
            Self for method chaining
        """
        self.paths.pop(path, None)
        return self

    def get_all_paths(self) -> dict[str, PathItem | Reference]:
        """
        Get all paths.

        Returns:
            A dictionary of all paths and their path items
        """
        return self.paths.copy()

    def to_dict(self) -> dict[str, Any]:
        """Convert the Paths object to a dictionary representation."""
        return {path: path_item.to_dict() for path, path_item in self.paths.items()}

    def __repr__(self) -> str:
        return f"Paths({len(self.paths)} paths)"

    def __len__(self) -> int:
        """Get the number of paths."""
        return len(self.paths)

    def __contains__(self, path: str) -> bool:
        """Check if a path exists."""
        return path in self.paths

    def __iter__(self):
        """Iterate over path names."""
        return iter(self.paths)
