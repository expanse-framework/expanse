from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from expanse.schematic.openapi.reference import Reference
    from expanse.schematic.openapi.response import Response


class Responses:
    """
    A container for the expected responses of an operation.
    The container maps a HTTP response code to the expected response.

    The documentation is not necessarily expected to cover all possible HTTP response codes
    because they may not be known in advance. However, documentation is expected to cover
    a successful operation response and any known errors.

    The default MAY be used as a default response object for all HTTP codes
    that are not covered individually by the Responses Object.

    The Responses Object MUST contain at least one response code, and if only one response code
    is provided it SHOULD be the response for a successful operation call.
    """

    def __init__(self) -> None:
        """Initialize a Responses object."""
        self.responses: dict[str, Response | Reference] = {}
        self.default: Response | Reference | None = None

    def add_response(
        self, status_code: str, response: "Response | Reference"
    ) -> "Responses":
        """
        Add a response for a specific HTTP status code.

        Args:
            status_code: Any HTTP status code can be used as the property name, but only one
                        property per code, to describe the expected response for that HTTP status code.
                        This field MUST be enclosed in quotation marks (for example, "200") for
                        compatibility between JSON and YAML. To define a range of response codes,
                        this field MAY contain the uppercase wildcard character X. For example,
                        2XX represents all response codes between [200-299].
            response: The response object or reference

        Returns:
            Self for method chaining
        """
        self.responses[status_code] = response
        return self

    def set_default(self, response: "Response | Reference") -> "Responses":
        """
        Set the default response object for all HTTP codes that are not covered individually.

        Args:
            response: The documentation of responses other than the ones declared for specific
                     HTTP response codes. Use this field to cover undeclared responses.

        Returns:
            Self for method chaining
        """
        self.default = response
        return self

    def get_response(self, status_code: str) -> "Response | Reference | None":
        """
        Get a response by status code.

        Args:
            status_code: The HTTP status code

        Returns:
            The response object or reference if found, None otherwise
        """
        return self.responses.get(status_code)

    def get_default(self) -> "Response | Reference | None":
        """
        Get the default response.

        Returns:
            The default response object or reference if set, None otherwise
        """
        return self.default

    def remove_response(self, status_code: str) -> "Responses":
        """
        Remove a response by status code.

        Args:
            status_code: The HTTP status code to remove

        Returns:
            Self for method chaining
        """
        self.responses.pop(status_code, None)
        return self

    def clear_default(self) -> "Responses":
        """
        Clear the default response.

        Returns:
            Self for method chaining
        """
        self.default = None
        return self

    def get_all_responses(self) -> dict[str, "Response | Reference"]:
        """
        Get all responses.

        Returns:
            A dictionary of all responses mapped by status code
        """
        return self.responses.copy()

    def has_response(self, status_code: str) -> bool:
        """
        Check if a response exists for a status code.

        Args:
            status_code: The HTTP status code

        Returns:
            True if a response exists for the status code, False otherwise
        """
        return status_code in self.responses

    def has_default(self) -> bool:
        """
        Check if a default response is set.

        Returns:
            True if a default response is set, False otherwise
        """
        return self.default is not None

    def is_empty(self) -> bool:
        """
        Check if the responses object is empty.

        Returns:
            True if no responses are defined (including default), False otherwise
        """
        return len(self.responses) == 0 and self.default is None

    def to_dict(self) -> dict[str, Any]:
        """Convert the Responses object to a dictionary representation."""
        result: dict[str, Any] = {}

        # Add all status code responses
        for status_code, response in self.responses.items():
            result[status_code] = response.to_dict()

        # Add default response if present
        if self.default is not None:
            result["default"] = self.default.to_dict()

        return result

    def __repr__(self) -> str:
        response_count = len(self.responses)
        has_default = self.default is not None

        parts = []
        if response_count > 0:
            parts.append(f"{response_count} responses")
        if has_default:
            parts.append("default")

        if parts:
            return f"Responses({', '.join(parts)})"
        else:
            return "Responses(empty)"

    def __len__(self) -> int:
        """Get the total number of responses (including default)."""
        count = len(self.responses)
        if self.default is not None:
            count += 1
        return count

    def __contains__(self, status_code: str) -> bool:
        """Check if a response exists for a status code."""
        return status_code in self.responses

    def __iter__(self):
        """Iterate over status codes."""
        return iter(self.responses)
