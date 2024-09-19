from pathlib import Path

from treat.mock import Mockery  # type: ignore[import-untyped]

from expanse.asynchronous.core.application import Application
from expanse.asynchronous.database.console.commands.make_model import (
    MakeModelCommand,  # noqa: F401
)
from expanse.asynchronous.testing.command_tester import CommandTester


async def test_make_model(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    mockery.mock(app).should_receive("path").with_("models").and_return(
        tmp_path / "models"
    )
    mockery.mock(app).should_receive("path").with_(
        "models/model.py", relative=True
    ).and_return("models/model.py")
    mockery.mock(app).should_receive("path").with_(
        "models/user.py", relative=True
    ).and_return("models/user.py")

    command = command_tester.command("make model")

    assert await command.run("User") == 0

    expected = """
  - Generated file: models/user.py
"""

    assert command.output.fetch() == expected

    assert tmp_path.joinpath("models/user.py").exists()

    model_content = """\
from expanse.common.database.orm.model import Model


class User(Model):

    __tablename__: str = "users"
"""

    assert tmp_path.joinpath("models/user.py").read_text() == model_content


async def test_make_model_with_table_name(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    mockery.mock(app).should_receive("path").with_("models").and_return(
        tmp_path / "models"
    )
    mockery.mock(app).should_receive("path").with_(
        "models/model.py", relative=True
    ).and_return("models/model.py")
    mockery.mock(app).should_receive("path").with_(
        "models/user.py", relative=True
    ).and_return("models/user.py")

    command = command_tester.command("make model")

    assert await command.run("User --table my_users") == 0

    expected = """
  - Generated file: models/user.py
"""

    assert command.output.fetch() == expected

    assert tmp_path.joinpath("models/user.py").exists()

    base_model_content = """\
from expanse.common.database.orm.model import Model


class User(Model):

    __tablename__: str = "my_users"
"""

    assert tmp_path.joinpath("models/user.py").read_text() == base_model_content
