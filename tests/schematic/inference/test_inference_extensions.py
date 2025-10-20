from __future__ import annotations

from expanse.routing.route import Route
from expanse.schematic.inference.code_analyzer import CodeAnalyzer
from expanse.schematic.inference.extensions.abort_detector import AbortDetector
from expanse.schematic.inference.extensions.http_exception_detector import (
    HTTPExceptionDetector,
)
from expanse.schematic.inference.inference import Inference
from expanse.schematic.inference.inference import InferenceResult


def test_abort_detector_detects_abort_calls():
    """Test that abort() calls are detected and converted to errors."""

    def handler():
        if not user:
            abort(404, "User not found")
        if not authorized:
            abort(403)

    route = Route.get("/users", handler)
    code_analyzer = CodeAnalyzer()
    code_analysis = code_analyzer.analyze(handler)

    result = InferenceResult()
    detector = AbortDetector()
    detector.infer(route, code_analysis, result)

    assert len(result.errors) == 2

    # Check first error
    assert result.errors[0].status_code == 404
    assert result.errors[0].description == "User not found"
    assert result.errors[0].exception_type == "HTTPException"

    # Check second error (should have default message)
    assert result.errors[1].status_code == 403
    assert "Forbidden" in result.errors[1].description


def test_http_exception_detector_detects_raises():
    """Test that HTTPException raises are detected."""

    def handler():
        if not user:
            raise HTTPException(404, "User not found")
        if not valid:
            raise HTTPException(400, "Bad request")

    route = Route.get("/users", handler)
    code_analyzer = CodeAnalyzer()
    code_analysis = code_analyzer.analyze(handler)

    result = InferenceResult()
    detector = HTTPExceptionDetector()
    detector.infer(route, code_analysis, result)

    assert len(result.errors) == 2

    assert result.errors[0].status_code == 404
    assert result.errors[0].description == "User not found"

    assert result.errors[1].status_code == 400
    assert result.errors[1].description == "Bad request"


def test_inference_runs_multiple_extensions():
    """Test that multiple inference extensions work together."""

    def handler():
        abort(403, "Forbidden")
        raise HTTPException(500, "Server error")

    route = Route.get("/users", handler)
    code_analyzer = CodeAnalyzer()
    code_analysis = code_analyzer.analyze(handler)

    inference = Inference()
    inference.add_extension(AbortDetector())
    inference.add_extension(HTTPExceptionDetector())

    result = inference.infer(route, handler, code_analysis)

    # Should detect both abort and raise
    assert len(result.errors) == 2
    assert any(e.status_code == 403 for e in result.errors)
    assert any(e.status_code == 500 for e in result.errors)
