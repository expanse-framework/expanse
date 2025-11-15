from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.schematic.inference.code_analyzer import CodeAnalysisResult
    from expanse.schematic.inference.inference import InferenceResult
    from expanse.schematic.support.route_info import RouteInfo


class HTTPExceptionDetector:
    """
    Detects HTTPException being raised and infers HTTP errors.
    """

    def infer(
        self,
        route_info: RouteInfo,
        code_analysis: CodeAnalysisResult,
        result: InferenceResult,
    ) -> None:
        """
        Detect HTTPException raises and add them as inferred errors.
        """
        from expanse.schematic.inference.inference import InferredError

        for exc in code_analysis.exceptions_raised:
            # Check if it's an HTTPException
            if (
                (
                    exc.exception_type == "HTTPException"
                    or exc.exception_type.endswith(".HTTPException")
                )
                and exc.args
                and isinstance(exc.args[0], int)
            ):
                status_code = exc.args[0]

                # Extract message (second argument)
                message = None
                if len(exc.args) > 1 and isinstance(exc.args[1], str):
                    message = exc.args[1]

                # Generate description
                if message:
                    description = message
                else:
                    try:
                        description = HTTPStatus(status_code).phrase
                    except ValueError:
                        description = f"HTTP {status_code}"

                result.errors.append(
                    InferredError(
                        status_code=status_code,
                        description=description,
                        exception_type="HTTPException",
                    )
                )
