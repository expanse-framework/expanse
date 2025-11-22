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
        self.responses: dict[str, Response | Reference] = {}
        self.default: Response | Reference | None = None

    def add_response(
        self, status_code: str, response: Response | Reference
    ) -> Responses:
        self.responses[status_code] = response
        return self

    def set_default(self, response: Response | Reference) -> Responses:
        self.default = response
        return self

    def get_response(self, status_code: str) -> Response | Reference | None:
        return self.responses.get(status_code)

    def get_default(self) -> Response | Reference | None:
        return self.default

    def remove_response(self, status_code: str) -> Responses:
        self.responses.pop(status_code, None)
        return self

    def get_all_responses(self) -> dict[str, Response | Reference]:
        return self.responses.copy()

    def has_response(self, status_code: str) -> bool:
        return status_code in self.responses

    def has_default(self) -> bool:
        return self.default is not None

    def is_empty(self) -> bool:
        return len(self.responses) == 0 and self.default is None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}

        # Add all status code responses
        for status_code, response in self.responses.items():
            result[status_code] = response.to_dict()

        # Add default response if present
        if self.default is not None:
            result["default"] = self.default.to_dict()

        return result

    def __len__(self) -> int:
        count = len(self.responses)
        if self.default is not None:
            count += 1
        return count

    def __contains__(self, status_code: str) -> bool:
        return status_code in self.responses

    def __iter__(self):
        return iter(self.responses)
