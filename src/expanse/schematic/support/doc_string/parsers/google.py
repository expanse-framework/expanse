import re

from expanse.schematic.support.doc_string.doc_string_info import DocStringInfo
from expanse.schematic.support.doc_string.doc_string_info import ParameterDoc
from expanse.schematic.support.doc_string.doc_string_info import RaisesDoc
from expanse.schematic.support.doc_string.parsers.parser import DocStringParser


class GoogleDocStringParser(DocStringParser):
    @classmethod
    def can_handle(cls, doc_string: str) -> bool:
        return (
            re.search(r"(Args|Returns|Raises|Yields|Examples):\s*$", doc_string, re.M)
            is not None
        )

    @classmethod
    def parse(cls, doc_string: str) -> DocStringInfo:
        info = DocStringInfo()
        lines = doc_string.split("\n")

        # Parse sections
        current_section = None
        section_lines: list[str] = []

        for line in lines:
            stripped = line.strip()

            # Check for section headers
            if stripped in ("Args:", "Arguments:", "Parameters:"):
                if current_section:
                    cls._process_google_section(current_section, section_lines, info)
                current_section = "args"
                section_lines = []
            elif stripped in ("Returns:", "Return:"):
                if current_section:
                    cls._process_google_section(current_section, section_lines, info)
                current_section = "returns"
                section_lines = []
            elif stripped in ("Raises:", "Raise:"):
                if current_section:
                    cls._process_google_section(current_section, section_lines, info)
                current_section = "raises"
                section_lines = []
            elif stripped in ("Examples:", "Example:"):
                if current_section:
                    cls._process_google_section(current_section, section_lines, info)
                current_section = "examples"
                section_lines = []
            elif current_section:
                section_lines.append(line)
            elif not info.summary and stripped:
                info.summary = stripped
            elif stripped:
                # Part of description
                if info.description:
                    info.description += "\n" + stripped
                else:
                    info.description = stripped

        # Process last section
        if current_section:
            cls._process_google_section(current_section, section_lines, info)

        return info

    @classmethod
    def _process_google_section(
        cls, section: str, lines: list[str], info: DocStringInfo
    ) -> None:
        if section == "args":
            # Parse parameters: "name (type): description" or "name: description"
            current_param = None
            current_desc = []

            for line in lines:
                # Match parameter definition
                match = re.match(r"\s*(\w+)\s*(\([^)]+\))?\s*:\s*(.*)", line)
                if match:
                    # Save previous parameter
                    if current_param:
                        info.parameters[current_param.name] = current_param

                    name = match.group(1)
                    type_hint = match.group(2).strip("()") if match.group(2) else None
                    description = match.group(3).strip()

                    current_param = ParameterDoc(
                        name=name, description=description, type_hint=type_hint
                    )
                    current_desc = [description] if description else []
                elif current_param and line.strip():
                    # Continuation of description
                    current_desc.append(line.strip())
                    current_param.description = " ".join(current_desc)

            # Save last parameter
            if current_param:
                info.parameters[current_param.name] = current_param

        elif section == "returns":
            # Join all lines as return description
            return_text = " ".join(line.strip() for line in lines if line.strip())
            info.returns = return_text

        elif section == "raises":
            # Parse raises: "ExceptionType: description" or "ExceptionType: (status) description"
            for line in lines:
                match = re.match(r"\s*(\w+)\s*: (?:\((\d+)\))?\s*(.*)", line)
                if match:
                    exception = match.group(1)
                    status_code = int(match.group(2)) if match.group(2) else 500
                    description = match.group(3).strip()

                    # Try to extract status code from description
                    if not status_code:
                        status_match = re.search(r"\s*\((\d{3})\)\s", description)
                        if status_match:
                            status_code = int(status_match.group(1))

                    info.raises.append(
                        RaisesDoc(
                            exception=exception,
                            description=description.strip().removeprefix(
                                f"({status_code}) "
                            )
                            if status_code
                            else description.strip(),
                            status_code=status_code,
                        )
                    )

        elif section == "examples":
            example_text = "\n".join(lines)
            if example_text.strip():
                info.examples.append(example_text.strip())
