from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol

from expanse.schematic.inference.code_analyzer import CodeAnalyzer


if TYPE_CHECKING:
    from collections.abc import Callable

    from expanse.schematic.inference.code_analyzer import CodeAnalysisResult
    from expanse.schematic.support.route_info import RouteInfo


@dataclass
class InferredError:
    """Information about an inferred HTTP error."""

    status_code: int
    description: str
    exception_type: str | None = None


@dataclass
class InferredResponse:
    """Information about an inferred response."""

    status_code: int = 200
    content: Any = None
    content_type: str | None = None


@dataclass
class InferenceResult:
    """Results from code inference."""

    errors: list[InferredError] = field(default_factory=list)
    responses: list[InferredResponse] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class InferenceExtension(Protocol):
    """Protocol for inference extensions."""

    def infer(
        self,
        route_info: RouteInfo,
        code_analysis: CodeAnalysisResult,
        result: InferenceResult,
    ) -> None: ...


class Inference:
    def __init__(self) -> None:
        self._extensions: list[InferenceExtension] = []
        self._analyzer: CodeAnalyzer = CodeAnalyzer()
        self._index: dict[Callable, CodeAnalysisResult] = {}

    def add_extension(self, extension: InferenceExtension) -> None:
        self._extensions.append(extension)

    def infer(self, route_info: RouteInfo) -> InferenceResult:
        result = InferenceResult()

        func = route_info.func

        code_analysis = self._analyzer.analyze(func)

        # Run all extensions
        for extension in self._extensions:
            extension.infer(route_info, code_analysis, result)

        return result
