import re

from expanse.schematic.support.doc_string.doc_string_info import DocStringInfo
from expanse.schematic.support.doc_string.doc_string_info import ParameterDoc
from expanse.schematic.support.doc_string.doc_string_info import RaisesDoc
from expanse.schematic.support.doc_string.parsers.parser import DocStringParser


class SphinxDocStringParser(DocStringParser):
    @classmethod
    def can_handle(cls, doc_string: str) -> bool:
        return (
            re.search(
                r":(param\s+\w+|type\s+\w+|returns?|raises\s+\w+?|rtype):", doc_string
            )
            is not None
        )

    @classmethod
    def parse(cls, doc_string: str) -> DocStringInfo:
        info = DocStringInfo()
        lines = doc_string.split("\n")

        # Extract summary (first non-empty line before first section)
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith(":") and not info.summary:
                info.summary = stripped
                continue

            if stripped.startswith(":"):
                break

            info.description += line.strip()

        # Parse Sphinx fields
        for line in lines:
            # :param name: description
            param_match = re.match(r":param\s+(\w+):\s*(.*)", line.strip())
            if param_match:
                name = param_match.group(1)
                description = param_match.group(2)
                info.parameters[name] = ParameterDoc(name=name, description=description)
                continue

            # :type name: type
            type_match = re.match(r":type\s+(\w+):\s*(.*)", line.strip())
            if type_match:
                name = type_match.group(1)
                type_hint = type_match.group(2)
                if name in info.parameters:
                    info.parameters[name].type_hint = type_hint
                else:
                    info.parameters[name] = ParameterDoc(
                        name=name, description="", type_hint=type_hint
                    )
                continue

            # :returns: or :return: description
            returns_match = re.match(r":returns?:\s*(.*)", line.strip())
            if returns_match:
                info.returns = returns_match.group(1)
                continue

            # :rtype: type
            rtype_match = re.match(r":rtype:\s*(.*)", line.strip())
            if rtype_match:
                info.return_type = rtype_match.group(1)
                continue

            # :raises Exception: description or :raise Exception: (status) description
            raises_match = re.match(r":raises?\s+(\w+):\s*(.*)", line.strip())
            if raises_match:
                exception = raises_match.group(1)
                description = raises_match.group(2)

                # Try to extract status code from description
                status_code = 500
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
                continue

        return info
