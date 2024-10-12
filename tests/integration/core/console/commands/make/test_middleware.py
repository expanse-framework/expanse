from pathlib import Path

from treat.mock import Mockery

from expanse.core.application import Application
from expanse.testing.command_tester import CommandTester


async def test_make_middleware(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    mockery.mock(app).should_receive("path").with_("http/middleware").and_return(
        tmp_path / "http/middleware"
    )
    mockery.mock(app).should_receive("path").with_(
        "http/middleware/validate_token.py", relative=True
    ).and_return("http/middleware/validate_token.py")

    command = command_tester.command("make middleware")

    assert command.run("validate_token") == 0

    expected = """
  - Generated file: http/middleware/validate_token.py
"""

    assert command.output.fetch() == expected

    assert tmp_path.joinpath("http/middleware/validate_token.py").exists()

    model_content = """\
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.types.http.middleware import RequestHandler


class ValidateToken:

    async def handle(
        self, request: Request, next_call: RequestHandler
    ) -> Response:
        return await next_call(request)
"""

    assert (
        tmp_path.joinpath("http/middleware/validate_token.py").read_text()
        == model_content
    )


async def test_make_middleware_with_existing_file(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    mockery.mock(app).should_receive("path").with_("http/middleware").and_return(
        tmp_path / "http/middleware"
    )
    mockery.mock(app).should_receive("path").with_(
        "http/middleware/validate_token.py", relative=True
    ).and_return("http/middleware/validate_token.py")

    tmp_path.joinpath("http/middleware").mkdir(parents=True)
    tmp_path.joinpath("http/middleware/validate_token.py").touch()

    command = command_tester.command("make middleware")

    assert command.run("validate_token") == 1

    expected = """\
  - The middleware file http/middleware/validate_token.py already exists.
"""

    assert command.output.fetch() == expected
