from pathlib import Path

from treat.mock import Mockery

from expanse.core.application import Application
from expanse.testing.command_tester import CommandTester


async def test_make_controller(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    mockery.mock(app).should_receive("path").with_("http/controllers").and_return(
        tmp_path / "http/controllers"
    )
    mockery.mock(app).should_receive("path").with_(
        "http/controllers/user.py", relative=True
    ).and_return("http/controllers/user.py")

    command = command_tester.command("make controller")

    assert command.run("user") == 0

    expected = """
  - Generated file: http/controllers/user.py
"""

    assert command.output.fetch() == expected

    assert tmp_path.joinpath("http/controllers/user.py").exists()

    model_content = """\
class UserController:

    ...
"""

    assert tmp_path.joinpath("http/controllers/user.py").read_text() == model_content


async def test_make_middleware_with_existing_file(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    mockery.mock(app).should_receive("path").with_("http/controllers").and_return(
        tmp_path / "http/controllers"
    )
    mockery.mock(app).should_receive("path").with_(
        "http/controllers/user.py", relative=True
    ).and_return("http/controllers/user.py")

    tmp_path.joinpath("http/controllers").mkdir(parents=True)
    tmp_path.joinpath("http/controllers/user.py").touch()

    command = command_tester.command("make controller")

    assert command.run("UserController") == 1

    expected = """\
  - The middleware file http/controllers/user.py already exists.
"""

    assert command.output.fetch() == expected
