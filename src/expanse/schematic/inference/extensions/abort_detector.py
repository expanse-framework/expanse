from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.schematic.inference.code_analyzer import CodeAnalysisResult
    from expanse.schematic.inference.inference import InferenceResult
    from expanse.schematic.support.route_info import RouteInfo


class AbortDetector:
    """
    Detects calls to abort() helper function and infers HTTP errors.
    """

    def infer(
        self,
        route_info: RouteInfo,
        code_analysis: CodeAnalysisResult,
        result: InferenceResult,
    ) -> None:
        """
        Detect abort() calls and add them as inferred errors.
        """
        from expanse.schematic.inference.inference import InferredError

        for call in code_analysis.function_calls:
            # Check if it's an abort call
            if (
                (call.name == "abort" or call.name.endswith(".abort"))
                and call.args
                and isinstance(call.args[0], int)
            ):
                status_code = call.args[0]

                # Extract message (second argument or from kwargs)
                message = None
                if len(call.args) > 1 and isinstance(call.args[1], str):
                    message = call.args[1]
                elif "message" in call.kwargs and isinstance(
                    call.kwargs["message"], str
                ):
                    message = call.kwargs["message"]

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
