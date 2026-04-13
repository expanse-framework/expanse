from __future__ import annotations

import sys

from dataclasses import dataclass
from types import ModuleType
from typing import TYPE_CHECKING
from unittest.mock import PropertyMock

import pytest

from expanse.messenger.handler_locator import HandlerLocator
from expanse.messenger.registry import Registry
from expanse.messenger.utils import message_handler


if TYPE_CHECKING:
    from pathlib import Path

    from expanse.core.application import Application


@dataclass
class MyMessage:
    value: str


@dataclass
class OtherMessage:
    data: int


@message_handler()
async def handle_my_message(message: MyMessage) -> None:
    pass


@message_handler()
async def handle_other_message(message: OtherMessage) -> None:
    pass


@pytest.fixture()
def registry() -> Registry:
    return Registry()


@pytest.fixture()
def app(tmp_path: Path) -> Application:
    from unittest.mock import MagicMock

    mock_app = MagicMock(spec=["base_path"])
    type(mock_app).base_path = PropertyMock(return_value=tmp_path)

    return mock_app


@pytest.fixture()
def locator(app: Application, registry: Registry) -> HandlerLocator:
    return HandlerLocator(app, registry)


def test_locate_handlers_in_module(locator: HandlerLocator) -> None:
    # The @message_handler() decorator registers handlers on this test module
    this_module = sys.modules[__name__]

    result = locator.locate_handlers_in_module(this_module)

    assert len(result) == 2
    handlers = {r["handler"] for r in result}
    assert handle_my_message in handlers
    assert handle_other_message in handlers

    my_def = next(r for r in result if r["handler"] is handle_my_message)
    assert my_def["message_type"] is MyMessage

    other_def = next(r for r in result if r["handler"] is handle_other_message)
    assert other_def["message_type"] is OtherMessage


def test_locate_handlers_in_module_with_no_handlers(
    locator: HandlerLocator,
) -> None:
    module = ModuleType("empty_module")

    result = locator.locate_handlers_in_module(module)

    assert result == []


def test_register_handlers_from_module(
    locator: HandlerLocator, registry: Registry
) -> None:
    this_module = sys.modules[__name__]

    locator.register_handlers_from_module(this_module)

    assert registry.get_handlers(MyMessage) == [handle_my_message]
    assert registry.get_handlers(OtherMessage) == [handle_other_message]


def test_locate_handlers_in_file(locator: HandlerLocator, app: Application) -> None:
    base_path = app.base_path
    handler_file = base_path / "test_handlers_mod.py"
    handler_file.write_text(
        """\
from dataclasses import dataclass

from expanse.messenger.utils import message_handler


@dataclass
class FileMessage:
    value: str


@message_handler()
async def handle_file_message(message: FileMessage) -> None:
    pass
"""
    )

    sys.path.insert(0, str(base_path))
    try:
        result = locator.locate_handlers_in_file(handler_file)

        assert len(result) == 1
        assert result[0]["handler"].__name__ == "handle_file_message"
    finally:
        sys.path.remove(str(base_path))
        sys.modules.pop("test_handlers_mod", None)


def test_locate_handlers_in_directory(
    locator: HandlerLocator, app: Application
) -> None:
    base_path = app.base_path
    handlers_dir = base_path / "handlers"
    handlers_dir.mkdir()

    (handlers_dir / "handler_a.py").write_text(
        """\
from dataclasses import dataclass

from expanse.messenger.utils import message_handler


@dataclass
class MessageA:
    value: str


@message_handler()
async def handle_a(message: MessageA) -> None:
    pass
"""
    )

    (handlers_dir / "handler_b.py").write_text(
        """\
from dataclasses import dataclass

from expanse.messenger.utils import message_handler


@dataclass
class MessageB:
    data: int


@message_handler()
async def handle_b(message: MessageB) -> None:
    pass
"""
    )

    sys.path.insert(0, str(base_path))
    try:
        result = locator.locate_handlers_in_directory(handlers_dir)

        assert len(result) == 2
        handler_names = {r["handler"].__name__ for r in result}
        assert handler_names == {"handle_a", "handle_b"}
    finally:
        sys.path.remove(str(base_path))
        sys.modules.pop("handlers.handler_a", None)
        sys.modules.pop("handlers.handler_b", None)


def test_register_handlers_from_directory(
    locator: HandlerLocator, registry: Registry, app: Application
) -> None:
    base_path = app.base_path
    handlers_dir = base_path / "reg_handlers"
    handlers_dir.mkdir()

    (handlers_dir / "my_handler.py").write_text(
        """\
from dataclasses import dataclass

from expanse.messenger.utils import message_handler


@dataclass
class RegMessage:
    value: str


@message_handler()
async def handle_reg(message: RegMessage) -> None:
    pass
"""
    )

    sys.path.insert(0, str(base_path))
    try:
        locator.register_handlers_from_directory(handlers_dir)

        import importlib

        mod = importlib.import_module("reg_handlers.my_handler")
        assert len(registry.get_handlers(mod.RegMessage)) == 1
        assert registry.get_handlers(mod.RegMessage)[0].__name__ == "handle_reg"
    finally:
        sys.path.remove(str(base_path))
        sys.modules.pop("reg_handlers.my_handler", None)
