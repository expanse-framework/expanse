from __future__ import annotations

import re

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from collections.abc import Callable

    from expanse.openapi.config import OpenAPIConfig


class DocstringInfo:
    """Extracted information from a docstring."""

    def __init__(self) -> None:
        """Initialize docstring information."""
        self.summary: str | None = None
        self.description: str | None = None
        self.parameters: dict[str, str] = {}
        self.returns: str | None = None
        self.raises: dict[str, str] = {}
        self.examples: list[str] = []
        self.notes: list[str] = []
        self.deprecated: bool = False


class DocstringParser:
    """Parses function docstrings to extract OpenAPI documentation."""

    def __init__(self, config: OpenAPIConfig) -> None:
        """Initialize docstring parser with configuration."""
        self.config = config
        self.style = config.docstring_style

    def parse_docstring(self, func: Callable[..., Any]) -> DocstringInfo:
        """
        Parse a function's docstring and extract structured information.

        Args:
            func: The function whose docstring to parse

        Returns:
            DocstringInfo with extracted information
        """
        import inspect

        docstring = inspect.getdoc(func)
        if not docstring:
            return DocstringInfo()

        return self.parse_docstring_text(docstring)

    def parse_docstring_text(self, docstring: str) -> DocstringInfo:
        """
        Parse docstring text and extract structured information.

        Args:
            docstring: The docstring text to parse

        Returns:
            DocstringInfo with extracted information
        """
        info = DocstringInfo()

        # Normalize line endings and strip
        docstring = docstring.replace("\r\n", "\n").replace("\r", "\n").strip()

        if self.style == "auto":
            # Try to detect the style
            if self._is_google_style(docstring):
                self._parse_google_style(docstring, info)
            elif self._is_sphinx_style(docstring):
                self._parse_sphinx_style(docstring, info)
            elif self._is_numpy_style(docstring):
                self._parse_numpy_style(docstring, info)
            else:
                self._parse_plain_style(docstring, info)
        elif self.style == "google":
            self._parse_google_style(docstring, info)
        elif self.style == "sphinx":
            self._parse_sphinx_style(docstring, info)
        elif self.style == "numpy":
            self._parse_numpy_style(docstring, info)
        else:
            self._parse_plain_style(docstring, info)

        return info

    def _is_google_style(self, docstring: str) -> bool:
        """Check if docstring follows Google style."""
        google_sections = [
            "Args:",
            "Arguments:",
            "Parameters:",
            "Returns:",
            "Return:",
            "Yields:",
            "Yield:",
            "Raises:",
            "Raise:",
            "Note:",
            "Notes:",
            "Example:",
            "Examples:",
        ]
        return any(section in docstring for section in google_sections)

    def _is_sphinx_style(self, docstring: str) -> bool:
        """Check if docstring follows Sphinx style."""
        sphinx_patterns = [
            r":param\s+\w+:",
            r":type\s+\w+:",
            r":returns?:",
            r":rtype:",
            r":raises?\s+\w+:",
        ]
        return any(re.search(pattern, docstring) for pattern in sphinx_patterns)

    def _is_numpy_style(self, docstring: str) -> bool:
        """Check if docstring follows NumPy style."""
        numpy_sections = ["Parameters\n", "Returns\n", "Raises\n", "Examples\n"]
        return any(section in docstring for section in numpy_sections)

    def _parse_google_style(self, docstring: str, info: DocstringInfo) -> None:
        """Parse Google-style docstring."""
        lines = docstring.split("\n")
        current_section = None
        section_content = []
        summary_done = False

        for line in lines:
            stripped = line.strip()

            # Check for section headers
            if stripped.endswith(":") and stripped[:-1] in [
                "Args",
                "Arguments",
                "Parameters",
                "Returns",
                "Return",
                "Yields",
                "Yield",
                "Raises",
                "Raise",
                "Note",
                "Notes",
                "Example",
                "Examples",
            ]:
                # Process previous section
                if current_section and section_content:
                    self._process_google_section(
                        current_section.lower(), section_content, info
                    )

                current_section = stripped[:-1].lower()
                section_content = []
                continue

            # Process content
            if current_section:
                section_content.append(line)
            else:
                # This is part of the main description
                if not summary_done and stripped:
                    if not info.summary:
                        info.summary = stripped
                        summary_done = True
                    else:
                        if info.description:
                            info.description += "\n" + stripped
                        else:
                            info.description = stripped
                elif stripped:
                    if info.description:
                        info.description += "\n" + stripped
                    else:
                        info.description = stripped

        # Process final section
        if current_section and section_content:
            self._process_google_section(current_section, section_content, info)

    def _process_google_section(
        self, section: str, content: list[str], info: DocstringInfo
    ) -> None:
        """Process a section from Google-style docstring."""
        content_text = "\n".join(content).strip()

        if section in ["args", "arguments", "parameters"]:
            self._parse_parameters_section(content_text, info)
        elif section in ["returns", "return", "yields", "yield"]:
            info.returns = content_text
        elif section in ["raises", "raise"]:
            self._parse_raises_section(content_text, info)
        elif section in ["note", "notes"]:
            info.notes.append(content_text)
        elif section in ["example", "examples"]:
            info.examples.append(content_text)

    def _parse_sphinx_style(self, docstring: str, info: DocstringInfo) -> None:
        """Parse Sphinx-style docstring."""
        lines = docstring.split("\n")
        description_lines = []
        summary_done = False

        for line in lines:
            stripped = line.strip()

            # Check for Sphinx directives
            param_match = re.match(r":param\s+(\w+):\s*(.*)", stripped)
            if param_match:
                param_name, param_desc = param_match.groups()
                info.parameters[param_name] = param_desc.strip()
                continue

            returns_match = re.match(r":returns?:\s*(.*)", stripped)
            if returns_match:
                info.returns = returns_match.group(1).strip()
                continue

            raises_match = re.match(r":raises?\s+(\w+):\s*(.*)", stripped)
            if raises_match:
                exception_name, exception_desc = raises_match.groups()
                info.raises[exception_name] = exception_desc.strip()
                continue

            # Handle type annotations (skip them for now)
            if re.match(r":type\s+\w+:", stripped) or re.match(r":rtype:", stripped):
                continue

            # Regular content
            if stripped:
                if not summary_done and not info.summary:
                    info.summary = stripped
                    summary_done = True
                else:
                    description_lines.append(stripped)
            elif description_lines:
                description_lines.append("")

        if description_lines:
            info.description = "\n".join(description_lines).strip()

    def _parse_numpy_style(self, docstring: str, info: DocstringInfo) -> None:
        """Parse NumPy-style docstring."""
        sections = self._split_numpy_sections(docstring)

        for section_name, section_content in sections.items():
            if section_name == "summary":
                lines = section_content.strip().split("\n")
                if lines:
                    info.summary = lines[0].strip()
                    if len(lines) > 1:
                        info.description = "\n".join(lines[1:]).strip()
            elif section_name == "parameters":
                self._parse_numpy_parameters(section_content, info)
            elif section_name == "returns":
                info.returns = section_content.strip()
            elif section_name == "raises":
                self._parse_numpy_raises(section_content, info)
            elif section_name == "examples":
                info.examples.append(section_content.strip())
            elif section_name == "notes":
                info.notes.append(section_content.strip())

    def _split_numpy_sections(self, docstring: str) -> dict[str, str]:
        """Split NumPy-style docstring into sections."""
        sections = {"summary": ""}
        lines = docstring.split("\n")
        current_section = "summary"
        current_content = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Check if this line is a section header
            if (
                stripped
                and i + 1 < len(lines)
                and lines[i + 1].strip()
                and all(c == "-" for c in lines[i + 1].strip())
            ):
                # Save previous section
                if current_content:
                    sections[current_section] = "\n".join(current_content)

                # Start new section
                current_section = stripped.lower()
                current_content = []
                continue

            # Skip underline
            if stripped and all(c == "-" for c in stripped):
                continue

            current_content.append(line)

        # Save final section
        if current_content:
            sections[current_section] = "\n".join(current_content)

        return sections

    def _parse_numpy_parameters(self, content: str, info: DocstringInfo) -> None:
        """Parse NumPy-style parameters section."""
        lines = content.split("\n")
        current_param = None
        current_desc = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check for parameter definition: "param_name : type"
            param_match = re.match(r"(\w+)\s*:\s*(.+)?", stripped)
            if param_match and not line.startswith(" "):
                # Save previous parameter
                if current_param and current_desc:
                    info.parameters[current_param] = " ".join(current_desc).strip()

                # Start new parameter
                current_param = param_match.group(1)
                desc_part = param_match.group(2) or ""
                current_desc = [desc_part] if desc_part else []
            elif current_param and line.startswith("    "):
                # Continuation of parameter description
                current_desc.append(stripped)

        # Save final parameter
        if current_param and current_desc:
            info.parameters[current_param] = " ".join(current_desc).strip()

    def _parse_numpy_raises(self, content: str, info: DocstringInfo) -> None:
        """Parse NumPy-style raises section."""
        lines = content.split("\n")
        current_exception = None
        current_desc = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check for exception definition: "ExceptionType"
            if not line.startswith(" ") and stripped:
                # Save previous exception
                if current_exception and current_desc:
                    info.raises[current_exception] = " ".join(current_desc).strip()

                # Start new exception
                current_exception = stripped
                current_desc = []
            elif current_exception and line.startswith("    "):
                # Continuation of exception description
                current_desc.append(stripped)

        # Save final exception
        if current_exception and current_desc:
            info.raises[current_exception] = " ".join(current_desc).strip()

    def _parse_plain_style(self, docstring: str, info: DocstringInfo) -> None:
        """Parse plain docstring without specific format."""
        lines = docstring.split("\n")
        if lines:
            info.summary = lines[0].strip()
            if len(lines) > 1:
                description_lines = [line.rstrip() for line in lines[1:]]
                info.description = "\n".join(description_lines).strip()

    def _parse_parameters_section(self, content: str, info: DocstringInfo) -> None:
        """Parse parameters section from Google-style docstring."""
        lines = content.split("\n")
        current_param = None
        current_desc = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check for parameter definition
            param_match = re.match(r"(\w+)(?:\s*\([^)]+\))?\s*:\s*(.*)", stripped)
            if param_match:
                # Save previous parameter
                if current_param and current_desc:
                    info.parameters[current_param] = " ".join(current_desc).strip()

                # Start new parameter
                current_param = param_match.group(1)
                desc_part = param_match.group(2)
                current_desc = [desc_part] if desc_part else []
            elif current_param:
                # Continuation of parameter description
                current_desc.append(stripped)

        # Save final parameter
        if current_param and current_desc:
            info.parameters[current_param] = " ".join(current_desc).strip()

    def _parse_raises_section(self, content: str, info: DocstringInfo) -> None:
        """Parse raises section from Google-style docstring."""
        lines = content.split("\n")
        current_exception = None
        current_desc = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check for exception definition
            exception_match = re.match(r"(\w+):\s*(.*)", stripped)
            if exception_match:
                # Save previous exception
                if current_exception and current_desc:
                    info.raises[current_exception] = " ".join(current_desc).strip()

                # Start new exception
                current_exception = exception_match.group(1)
                desc_part = exception_match.group(2)
                current_desc = [desc_part] if desc_part else []
            elif current_exception:
                # Continuation of exception description
                current_desc.append(stripped)

        # Save final exception
        if current_exception and current_desc:
            info.raises[current_exception] = " ".join(current_desc).strip()

    def extract_http_status_codes(
        self, docstring_info: DocstringInfo
    ) -> dict[str, str]:
        """
        Extract HTTP status codes from docstring information.

        Args:
            docstring_info: Parsed docstring information

        Returns:
            Dictionary mapping status codes to descriptions
        """
        status_codes = {}

        # Check returns section for status codes
        if docstring_info.returns:
            codes = self._extract_status_codes_from_text(docstring_info.returns)
            status_codes.update(codes)

        # Check raises section for error codes
        for exception, description in docstring_info.raises.items():
            codes = self._extract_status_codes_from_text(f"{exception}: {description}")
            status_codes.update(codes)

        # Default success response if none specified
        if not status_codes:
            status_codes["200"] = "Success"

        return status_codes

    def _extract_status_codes_from_text(self, text: str) -> dict[str, str]:
        """Extract HTTP status codes from text."""
        status_codes = {}

        # Pattern to match HTTP status codes (3-digit numbers)
        code_pattern = r"\b([1-5]\d{2})\b"
        matches = re.findall(code_pattern, text)

        for code in matches:
            # Try to extract description around the code
            context_pattern = rf"\b{code}\b[:\-\s]*([^.\n]+)"
            context_match = re.search(context_pattern, text)
            if context_match:
                description = context_match.group(1).strip()
            else:
                description = self._get_default_status_description(code)

            status_codes[code] = description

        return status_codes

    def _get_default_status_description(self, code: str) -> str:
        """Get default description for HTTP status code."""
        default_descriptions = {
            "200": "OK",
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
        return default_descriptions.get(code, "Unknown")
