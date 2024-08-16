from __future__ import annotations

import re

from importlib import import_module
from importlib.util import module_from_spec
from importlib.util import spec_from_file_location
from types import NoneType
from typing import TYPE_CHECKING
from typing import Any
from typing import ForwardRef
from typing import _eval_type  # type: ignore[attr-defined]


if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType


def string_to_class(string: str) -> type[Any]:
    method_name: str | None = None
    parts = string.split(":", maxsplit=1)
    if len(parts) > 1:
        method_name = parts[-1]

    module_name, class_name = parts[0].rsplit(".", maxsplit=1)

    module = import_module(module_name)

    class_ = getattr(module, class_name)

    if not method_name:
        return class_

    return getattr(class_, method_name)


def module_from_path(path: Path, name: str | None = None) -> ModuleType | None:
    spec = spec_from_file_location(name or path.with_suffix("").name, path)

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


def class_to_name(class_: type | str) -> str:
    if isinstance(class_, str):
        return class_

    module = class_.__module__
    name = class_.__qualname__

    full_name = f"{module}.{name}" if module else name

    return full_name


def eval_type_lenient(
    value: Any, globalns: dict[str, Any] | None, localns: dict[str, Any] | None
) -> Any:
    if value is None:
        value = NoneType
    elif isinstance(value, str):
        value = ForwardRef(value, is_argument=False, is_class=True)

    try:
        return _eval_type(value, globalns, localns)
    except NameError:
        # the point of this function is to be tolerant to this case
        return value
