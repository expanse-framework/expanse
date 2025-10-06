from __future__ import annotations

import ast
import inspect
import textwrap

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from collections.abc import Callable

    from expanse.openapi.config import OpenAPIConfig


class CodePattern:
    """Represents a detected code pattern."""

    def __init__(
        self,
        pattern_type: str,
        confidence: float,
        data: dict[str, Any],
        line_number: int | None = None,
    ) -> None:
        """Initialize code pattern."""
        self.pattern_type = pattern_type
        self.confidence = confidence  # 0.0 to 1.0
        self.data = data
        self.line_number = line_number


class ResponsePattern(CodePattern):
    """Pattern for response-related code."""

    def __init__(
        self,
        status_code: int | str | None = None,
        content_type: str | None = None,
        schema: dict[str, Any] | None = None,
        condition: str | None = None,
        confidence: float = 1.0,
        line_number: int | None = None,
    ) -> None:
        """Initialize response pattern."""
        data = {
            "status_code": status_code,
            "content_type": content_type,
            "schema": schema,
            "condition": condition,
        }
        super().__init__("response", confidence, data, line_number)

    @property
    def status_code(self) -> int | str | None:
        """Get status code."""
        return self.data["status_code"]

    @property
    def content_type(self) -> str | None:
        """Get content type."""
        return self.data["content_type"]

    @property
    def schema(self) -> dict[str, Any] | None:
        """Get response schema."""
        return self.data["schema"]


class ExceptionPattern(CodePattern):
    """Pattern for exception-related code."""

    def __init__(
        self,
        exception_type: str,
        status_code: int | str | None = None,
        message: str | None = None,
        condition: str | None = None,
        confidence: float = 1.0,
        line_number: int | None = None,
    ) -> None:
        """Initialize exception pattern."""
        data = {
            "exception_type": exception_type,
            "status_code": status_code,
            "message": message,
            "condition": condition,
        }
        super().__init__("exception", confidence, data, line_number)

    @property
    def exception_type(self) -> str:
        """Get exception type."""
        return self.data["exception_type"]

    @property
    def status_code(self) -> int | str | None:
        """Get status code."""
        return self.data["status_code"]


class ValidationPattern(CodePattern):
    """Pattern for validation-related code."""

    def __init__(
        self,
        validation_type: str,
        field_name: str | None = None,
        constraint: str | None = None,
        confidence: float = 1.0,
        line_number: int | None = None,
    ) -> None:
        """Initialize validation pattern."""
        data = {
            "validation_type": validation_type,
            "field_name": field_name,
            "constraint": constraint,
        }
        super().__init__("validation", confidence, data, line_number)


class CodeInferenceEngine:
    """Analyzes function code to infer OpenAPI behavior."""

    def __init__(self, config: OpenAPIConfig) -> None:
        """Initialize code inference engine."""
        self.config = config
        self.depth = config.inference_depth

    def analyze_function_code(self, func: Callable[..., Any]) -> list[CodePattern]:
        """
        Analyze function code and extract patterns.

        Args:
            func: The function to analyze

        Returns:
            List of detected code patterns
        """
        print(func)
        patterns = []

        try:
            # Get source code
            source = inspect.getsource(func)
            tree = ast.parse(textwrap.dedent(source))

            # Analyze AST
            visitor = CodeAnalysisVisitor(self.config)
            visitor.visit(tree)
            patterns.extend(visitor.patterns)

        except (OSError, TypeError, SyntaxError) as e:
            # Can't get source or parse it - not necessarily an error
            patterns.append(
                CodePattern(
                    "analysis_error",
                    0.0,
                    {"error": str(e), "reason": "source_unavailable"},
                )
            )

        return patterns

    def infer_response_schemas(self, patterns: list[CodePattern]) -> dict[str, Any]:
        """
        Infer response schemas from code patterns.

        Args:
            patterns: List of detected code patterns

        Returns:
            Dictionary mapping status codes to response schemas
        """
        responses = {}

        response_patterns = [p for p in patterns if isinstance(p, ResponsePattern)]

        for pattern in response_patterns:
            status_code = str(pattern.status_code or "200")

            response_info = {
                "description": self._get_status_description(status_code),
            }

            if pattern.content_type:
                content = {}
                if pattern.schema:
                    content[pattern.content_type] = {"schema": pattern.schema}
                else:
                    content[pattern.content_type] = {"schema": {"type": "object"}}

                response_info["content"] = content

            responses[status_code] = response_info

        # Add error responses from exception patterns
        exception_patterns = [p for p in patterns if isinstance(p, ExceptionPattern)]
        for pattern in exception_patterns:
            if pattern.status_code:
                status_code = str(pattern.status_code)
                if status_code not in responses:
                    responses[status_code] = {
                        "description": pattern.data.get("message")
                        or self._get_status_description(status_code),
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {"type": "string"},
                                        "message": {"type": "string"},
                                    },
                                }
                            }
                        },
                    }

        # Ensure at least one success response
        if not any(code.startswith("2") for code in responses):
            responses["200"] = {"description": "Success"}

        return responses

    def infer_request_validation(self, patterns: list[CodePattern]) -> dict[str, Any]:
        """
        Infer request validation from code patterns.

        Args:
            patterns: List of detected code patterns

        Returns:
            Dictionary with validation information
        """
        validation_info = {
            "required_fields": [],
            "field_constraints": {},
            "custom_validators": [],
        }

        validation_patterns = [p for p in patterns if isinstance(p, ValidationPattern)]

        for pattern in validation_patterns:
            if pattern.data.get("field_name"):
                field_name = pattern.data["field_name"]

                if pattern.validation_type == "required":
                    validation_info["required_fields"].append(field_name)

                if pattern.data.get("constraint"):
                    validation_info["field_constraints"][field_name] = pattern.data[
                        "constraint"
                    ]

        return validation_info

    def _get_status_description(self, status_code: str) -> str:
        """Get description for HTTP status code."""
        descriptions = {
            "200": "Success",
            "201": "Created",
            "202": "Accepted",
            "204": "No Content",
            "400": "Bad Request",
            "401": "Unauthorized",
            "403": "Forbidden",
            "404": "Not Found",
            "405": "Method Not Allowed",
            "409": "Conflict",
            "422": "Unprocessable Entity",
            "500": "Internal Server Error",
        }
        return descriptions.get(status_code, "Unknown")


class CodeAnalysisVisitor(ast.NodeVisitor):
    """AST visitor for analyzing code patterns."""

    def __init__(self, config: OpenAPIConfig) -> None:
        """Initialize visitor."""
        self.config = config
        self.patterns: list[CodePattern] = []
        self.current_line = 0

    def visit(self, node: ast.AST) -> None:
        """Visit AST node and track line numbers."""
        if hasattr(node, "lineno"):
            self.current_line = node.lineno
        super().visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        """Analyze return statements."""
        if node.value:
            pattern = self._analyze_return_value(node.value)
            if pattern:
                pattern.line_number = self.current_line
                self.patterns.append(pattern)

        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        """Analyze raise statements."""
        if node.exc:
            pattern = self._analyze_exception(node.exc)
            if pattern:
                pattern.line_number = self.current_line
                self.patterns.append(pattern)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Analyze function calls."""
        # Look for validation calls, model instantiation, etc.
        if isinstance(node.func, ast.Attribute):
            patterns = self._analyze_method_call(node)
            for pattern in patterns:
                pattern.line_number = self.current_line
                self.patterns.append(pattern)
        elif isinstance(node.func, ast.Name):
            patterns = self._analyze_function_call(node)
            for pattern in patterns:
                pattern.line_number = self.current_line
                self.patterns.append(pattern)

        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        """Analyze conditional statements."""
        # Extract condition for context
        condition = self._extract_condition_text(node.test)

        # Analyze body with condition context
        for stmt in node.body:
            if isinstance(stmt, ast.Return) and stmt.value:
                pattern = self._analyze_return_value(stmt.value)
                if pattern:
                    pattern.data["condition"] = condition
                    pattern.confidence *= 0.8  # Lower confidence for conditional
                    pattern.line_number = getattr(stmt, "lineno", self.current_line)
                    self.patterns.append(pattern)

        self.generic_visit(node)

    def _analyze_return_value(self, value_node: ast.AST) -> ResponsePattern | None:
        """Analyze return value to extract response information."""
        if isinstance(value_node, ast.Call):
            return self._analyze_response_call(value_node)
        elif isinstance(value_node, ast.Dict):
            return ResponsePattern(
                status_code=200,
                content_type="application/json",
                schema={"type": "object"},
                confidence=0.7,
            )
        elif isinstance(value_node, ast.List):
            return ResponsePattern(
                status_code=200,
                content_type="application/json",
                schema={"type": "array", "items": {"type": "object"}},
                confidence=0.7,
            )
        elif isinstance(value_node, ast.Constant):
            if isinstance(value_node.value, str):
                return ResponsePattern(
                    status_code=200,
                    content_type="text/plain",
                    schema={"type": "string"},
                    confidence=0.6,
                )

        return None

    def _analyze_response_call(self, call_node: ast.Call) -> ResponsePattern | None:
        """Analyze calls that create responses."""
        func_name = self._get_function_name(call_node.func)

        if not func_name:
            return None

        # Common response patterns
        if func_name.lower() in ["json", "html", "abort", "text"]:
            status_code = self._extract_status_code_from_call(call_node)
            content_type = self._infer_content_type_from_name(func_name)

            return ResponsePattern(
                status_code=status_code or 200,
                content_type=content_type,
                confidence=0.9,
            )

        # JSON/dict returns
        if func_name.lower() in ["json", "dict", "jsonify"]:
            return ResponsePattern(
                status_code=200,
                content_type="application/json",
                schema={"type": "object"},
                confidence=0.8,
            )

        return None

    def _analyze_exception(self, exc_node: ast.AST) -> ExceptionPattern | None:
        """Analyze exception raising."""
        if isinstance(exc_node, ast.Call):
            func_name = self._get_function_name(exc_node.func)
            if func_name:
                status_code = self._extract_status_code_from_call(exc_node)
                message = self._extract_message_from_call(exc_node)

                # Map common exception types to status codes
                if not status_code:
                    status_code = self._map_exception_to_status(func_name)

                return ExceptionPattern(
                    exception_type=func_name,
                    status_code=status_code,
                    message=message,
                    confidence=0.9,
                )

        return None

    def _analyze_method_call(self, call_node: ast.Call) -> list[CodePattern]:
        """Analyze method calls for patterns."""
        patterns = []

        if isinstance(call_node.func, ast.Attribute):
            attr_name = call_node.func.attr

            # Validation method calls
            if attr_name in ["validate", "validate_data", "is_valid"]:
                patterns.append(
                    ValidationPattern(
                        validation_type="data_validation",
                        confidence=0.7,
                    )
                )

        return patterns

    def _analyze_function_call(self, call_node: ast.Call) -> list[CodePattern]:
        """Analyze function calls for patterns."""
        patterns = []

        if isinstance(call_node.func, ast.Name):
            func_name = call_node.func.id

            # Model instantiation
            if func_name.endswith("Model") or func_name.endswith("Schema"):
                patterns.append(
                    ValidationPattern(
                        validation_type="model_validation",
                        confidence=0.8,
                    )
                )
            elif func_name == "abort":
                exception_pattern = self._analyze_exception(call_node)
                if exception_pattern:
                    patterns.append(exception_pattern)

        return patterns

    def _get_function_name(self, func_node: ast.AST) -> str | None:
        """Extract function name from call node."""
        if isinstance(func_node, ast.Name):
            return func_node.id
        elif isinstance(func_node, ast.Attribute):
            return func_node.attr
        return None

    def _extract_status_code_from_call(self, call_node: ast.Call) -> int | None:
        """Extract status code from function call arguments."""
        # Look for status_code keyword argument
        for keyword in call_node.keywords:
            if keyword.arg == "status_code" and isinstance(keyword.value, ast.Constant):
                if isinstance(keyword.value.value, int):
                    return keyword.value.value

        # Look for status code in positional arguments (common patterns)
        for i, arg in enumerate(call_node.args):
            if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                # If it looks like an HTTP status code
                if 100 <= arg.value <= 599:
                    return arg.value

        return None

    def _extract_message_from_call(self, call_node: ast.Call) -> str | None:
        """Extract message from function call arguments."""
        # Look for message in first string argument
        for arg in call_node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value

        # Look for message keyword argument
        for keyword in call_node.keywords:
            if keyword.arg in ["message", "detail"] and isinstance(
                keyword.value, ast.Constant
            ):
                if isinstance(keyword.value.value, str):
                    return keyword.value.value

        return None

    def _infer_content_type_from_name(self, func_name: str) -> str:
        """Infer content type from function name."""
        match func_name.lower():
            case "json":
                return "application/json"

            case "html":
                return "text/html"

            case "text":
                return "application/json"

            case _:
                return "application/json"

    def _map_exception_to_status(self, exception_name: str) -> int | None:
        """Map exception names to HTTP status codes."""
        mapping = {
            "HTTPException": None,  # Should have explicit status
            "BadRequest": 400,
            "Unauthorized": 401,
            "Forbidden": 403,
            "NotFound": 404,
            "MethodNotAllowed": 405,
            "Conflict": 409,
            "ValidationError": 422,
            "UnprocessableEntity": 422,
            "InternalServerError": 500,
        }

        return mapping.get(exception_name)

    def _extract_condition_text(self, test_node: ast.AST) -> str:
        """Extract readable text from condition node."""
        try:
            # Simple extraction - in a real implementation, you might want
            # to use ast.unparse (Python 3.9+) or astor library
            if isinstance(test_node, ast.Compare):
                left = self._node_to_string(test_node.left)
                if test_node.ops and test_node.comparators:
                    op = self._op_to_string(test_node.ops[0])
                    right = self._node_to_string(test_node.comparators[0])
                    return f"{left} {op} {right}"
            elif isinstance(test_node, ast.Name):
                return test_node.id
            elif isinstance(test_node, ast.Constant):
                return str(test_node.value)
        except Exception:
            pass

        return "condition"

    def _node_to_string(self, node: ast.AST) -> str:
        """Convert AST node to string representation."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Attribute):
            value = self._node_to_string(node.value)
            return f"{value}.{node.attr}"
        else:
            return "expr"

    def _op_to_string(self, op: ast.AST) -> str:
        """Convert comparison operator to string."""
        if isinstance(op, ast.Eq):
            return "=="
        elif isinstance(op, ast.NotEq):
            return "!="
        elif isinstance(op, ast.Lt):
            return "<"
        elif isinstance(op, ast.LtE):
            return "<="
        elif isinstance(op, ast.Gt):
            return ">"
        elif isinstance(op, ast.GtE):
            return ">="
        elif isinstance(op, ast.Is):
            return "is"
        elif isinstance(op, ast.IsNot):
            return "is not"
        elif isinstance(op, ast.In):
            return "in"
        elif isinstance(op, ast.NotIn):
            return "not in"
        else:
            return "op"
