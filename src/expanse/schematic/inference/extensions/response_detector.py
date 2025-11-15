from __future__ import annotations

import ast

from typing import TYPE_CHECKING
from typing import Any

from expanse.schematic.inference.inference import InferredResponse


if TYPE_CHECKING:
    from expanse.schematic.inference.code_analyzer import CodeAnalysisResult
    from expanse.schematic.inference.inference import InferenceResult
    from expanse.schematic.support.route_info import RouteInfo


class ResponseDetector:
    """
    Detects responses via calls to Response or specific helpers.
    """

    def infer(
        self,
        route_info: RouteInfo,
        code_analysis: CodeAnalysisResult,
        result: InferenceResult,
    ) -> None:
        for stmt in code_analysis.return_statements:
            if isinstance(stmt.value, ast.Call):
                self._infer_from_call(stmt.value, result)

    def _infer_from_call(self, call: ast.Call, result: InferenceResult) -> None:
        if not isinstance(call.func, ast.Name):
            return

        match call.func.id:
            case "Response" | "json":
                status_code, _content, content_type = self._extract_response_args(call)
                result.responses.append(
                    InferredResponse(status_code=status_code, content_type=content_type)
                )
            case _:
                return

    def _extract_response_args(self, call: ast.Call) -> tuple[int, Any, str | None]:
        status_code: int = 200
        content_type: str | None = None

        for idx, arg in enumerate(call.args):
            if (
                idx == 0
                and isinstance(arg, ast.Constant)
                and isinstance(arg.value, int)
            ):
                status_code = arg.value

        for keyword in call.keywords:
            if (
                keyword.arg == "status_code"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, int)
            ):
                status_code = keyword.value.value
            elif (
                keyword.arg == "media_type"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                content_type = keyword.value.value

        if content_type is None:
            match call.func.id:  # type: ignore[attr-defined]
                case "json":
                    content_type = "application/json"

        return (status_code, None, content_type)
