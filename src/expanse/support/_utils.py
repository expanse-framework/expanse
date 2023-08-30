from __future__ import annotations

import re

from importlib import import_module
from importlib.util import module_from_spec
from importlib.util import spec_from_file_location
from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType


def string_to_class(string: str) -> type[Any]:
    module_name, class_name = string.rsplit(".", maxsplit=1)

    module = import_module(module_name)

    return getattr(module, class_name)


def module_from_path(path: Path) -> ModuleType | None:
    spec = spec_from_file_location(path.with_suffix("").name, path)

    if spec is None:
        return None

    module = module_from_spec(spec)

    if module is None or spec.loader is None:
        return None

    spec.loader.exec_module(module)

    return module


def string_matches(string: str, pattern: str | list[str]) -> bool:
    if isinstance(pattern, str):
        pattern = [pattern]

    for pat in pattern:
        if string == pat:
            return True

        pat = re.escape(pat)
        pat = pat.replace(r"\*", ".*")

        if re.match(f"^{pat}", string):
            return True

    return False
