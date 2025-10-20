from __future__ import annotations

from expanse.schematic.inference.code_analyzer import CodeAnalyzer


def test_code_analyzer_detects_function_calls():
    """Test that function calls are detected."""

    def handler():
        print("Hello")
        abort(404, "Not found")
        some_function(1, 2, key="value")

    analyzer = CodeAnalyzer()
    result = analyzer.analyze(handler)

    assert len(result.function_calls) >= 2

    # Find abort call
    abort_calls = [c for c in result.function_calls if c.name == "abort"]
    assert len(abort_calls) == 1
    assert abort_calls[0].args[0] == 404
    assert abort_calls[0].args[1] == "Not found"


def test_code_analyzer_detects_exception_raises():
    """Test that raised exceptions are detected."""

    def handler():
        raise HTTPException(404, "Not found")
        raise ValueError("Invalid input")

    analyzer = CodeAnalyzer()
    result = analyzer.analyze(handler)

    assert len(result.exceptions_raised) == 2

    http_exc = result.exceptions_raised[0]
    assert http_exc.exception_type == "HTTPException"
    assert http_exc.args[0] == 404
    assert http_exc.args[1] == "Not found"

    value_error = result.exceptions_raised[1]
    assert value_error.exception_type == "ValueError"


def test_code_analyzer_detects_return_statements():
    """Test that return statements are detected."""

    def handler():
        if True:
            return {"success": True}
        return {"success": False}

    analyzer = CodeAnalyzer()
    result = analyzer.analyze(handler)

    assert len(result.return_statements) == 2


def test_code_analyzer_handles_method_calls():
    """Test that method calls are properly parsed."""

    def handler():
        obj.method()
        module.function()
        a.b.c.deep()

    analyzer = CodeAnalyzer()
    result = analyzer.analyze(handler)

    method_names = [c.name for c in result.function_calls]
    assert "obj.method" in method_names
    assert "module.function" in method_names
    assert "a.b.c.deep" in method_names


def test_code_analyzer_extracts_literal_values():
    """Test that literal values are extracted from calls."""

    def handler():
        func(123, "string", True, [1, 2, 3], {"key": "value"})

    analyzer = CodeAnalyzer()
    result = analyzer.analyze(handler)

    call = result.function_calls[0]
    assert call.args[0] == 123
    assert call.args[1] == "string"
    assert call.args[2] is True
    assert call.args[3] == [1, 2, 3]


def test_code_analyzer_handles_functions_without_source():
    """Test that built-in functions are handled gracefully."""

    # Built-in function
    analyzer = CodeAnalyzer()
    result = analyzer.analyze(print)

    # Should return empty result without crashing
    assert result.function_calls == []
    assert result.exceptions_raised == []
