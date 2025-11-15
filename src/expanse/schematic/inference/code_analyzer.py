from __future__ import annotations

import ast
import inspect
import textwrap

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class FunctionCall:
    """Represents a function call found in the code."""

    name: str
    args: list[Any] = field(default_factory=list)
    kwargs: dict[str, Any] = field(default_factory=dict)
    lineno: int = 0


@dataclass
class ExceptionRaise:
    """Represents an exception being raised."""

    exception_type: str
    args: list[Any] = field(default_factory=list)
    lineno: int = 0


@dataclass
class ReturnStatement:
    """Represents a return statement."""

    value: Any = None
    lineno: int = 0


@dataclass
class CodeAnalysisResult:
    """Results from analyzing code with AST."""

    function_calls: list[FunctionCall] = field(default_factory=list)
    exceptions_raised: list[ExceptionRaise] = field(default_factory=list)
    return_statements: list[ReturnStatement] = field(default_factory=list)
    imports: dict[str, str] = field(default_factory=dict)  # name -> module


class CodeAnalyzer:
    """
    Analyzes Python code using AST to extract information about function calls,
    exceptions raised, return statements, and more.
    """

    def analyze(self, func: Callable) -> CodeAnalysisResult:
        """
        Analyze a function's source code using AST.

        Args:
            func: The function to analyze

        Returns:
            CodeAnalysisResult with extracted information
        """
        result = CodeAnalysisResult()

        try:
            source = inspect.getsource(func)
            tree = ast.parse(textwrap.dedent(source))

            # Visit the AST
            visitor = _FunctionVisitor(result)
            visitor.visit(tree)

        except (OSError, TypeError):
            # Source not available (e.g., built-in, C extension)
            pass

        return result


class _FunctionVisitor(ast.NodeVisitor):
    """AST visitor to extract information from function code."""

    def __init__(self, result: CodeAnalysisResult) -> None:
        self.result = result

    def visit_Call(self, node: ast.Call) -> None:
        """Visit a function call node."""
        # Extract function name
        name = self._get_call_name(node.func)

        # Extract arguments
        args = []
        for arg in node.args:
            args.append(self._extract_value(arg))

        # Extract keyword arguments
        kwargs = {}
        for keyword in node.keywords:
            if keyword.arg:
                kwargs[keyword.arg] = self._extract_value(keyword.value)

        self.result.function_calls.append(
            FunctionCall(name=name, args=args, kwargs=kwargs, lineno=node.lineno)
        )

        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        """Visit a raise statement."""
        if node.exc:
            exception_type = self._get_exception_name(node.exc)
            args = []

            # If it's a Call node, extract arguments
            if isinstance(node.exc, ast.Call):
                for arg in node.exc.args:
                    args.append(self._extract_value(arg))

            self.result.exceptions_raised.append(
                ExceptionRaise(
                    exception_type=exception_type, args=args, lineno=node.lineno
                )
            )

        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        """Visit a return statement."""
        value = self._extract_value(node.value) if node.value else None

        self.result.return_statements.append(
            ReturnStatement(value=value, lineno=node.lineno)
        )

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Visit an import statement."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.result.imports[name] = alias.name

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit a from...import statement."""
        module = node.module or ""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.result.imports[name] = (
                f"{module}.{alias.name}" if module else alias.name
            )

        self.generic_visit(node)

    def _get_call_name(self, node: ast.expr) -> str:
        """Extract the function name from a call node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # Handle module.function or obj.method
            parts = []
            current = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value  # type: ignore[assignment]
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return "unknown"

    def _get_exception_name(self, node: ast.expr) -> str:
        """Extract the exception name from a raise node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            return self._get_call_name(node.func)
        elif isinstance(node, ast.Attribute):
            return self._get_call_name(node)
        return "Exception"

    def _extract_value(self, node: ast.expr | None) -> Any:
        """Extract a literal value from an AST node."""
        if node is None:
            return None
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return f"<var:{node.id}>"
        elif isinstance(node, ast.List):
            return [self._extract_value(elt) for elt in node.elts]
        elif isinstance(node, ast.Dict):
            return {
                self._extract_value(k): self._extract_value(v)
                for k, v in zip(node.keys, node.values)
            }
        elif isinstance(node, ast.Call):
            return node
        else:
            return f"<{node.__class__.__name__}>"
