from pathlib import Path

from treat.mock import Mockery

from expanse.core.application import Application
from expanse.testing.command_tester import CommandTester


async def test_make_job(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    mockery.mock(app).should_receive("path").with_("jobs").and_return(tmp_path / "jobs")
    mockery.mock(app).should_receive("path").with_(
        "jobs/foo.py", relative=True
    ).and_return("jobs/foo.py")

    command = command_tester.command("make job")

    assert command.run("foo") == 0

    expected = """
  - Generated file: jobs/foo.py
"""

    assert command.output.fetch() == expected

    assert tmp_path.joinpath("jobs/foo.py").exists()

    model_content = """\
from dataclasses import dataclass

from expanse.jobs.asynchronous.job import Job


@dataclass
class FooJobPayload: ...


class FooJob(Job[FooJobPayload]):

    async def execute(self) -> None:
        pass
"""

    assert tmp_path.joinpath("jobs/foo.py").read_text() == model_content


async def test_make_job_sync(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    mockery.mock(app).should_receive("path").with_("jobs").and_return(tmp_path / "jobs")
    mockery.mock(app).should_receive("path").with_(
        "jobs/foo.py", relative=True
    ).and_return("jobs/foo.py")

    command = command_tester.command("make job")

    assert command.run("foo --sync") == 0

    expected = """
  - Generated file: jobs/foo.py
"""

    assert command.output.fetch() == expected

    assert tmp_path.joinpath("jobs/foo.py").exists()

    model_content = """\
from dataclasses import dataclass

from expanse.jobs.synchronous.job import Job


@dataclass
class FooJobPayload: ...


class FooJob(Job[FooJobPayload]):

    def execute(self) -> None:
        pass
"""

    assert tmp_path.joinpath("jobs/foo.py").read_text() == model_content


async def test_make_job_with_existing_file(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    mockery.mock(app).should_receive("path").with_("jobs").and_return(tmp_path / "jobs")
    mockery.mock(app).should_receive("path").with_(
        "jobs/foo.py", relative=True
    ).and_return("jobs/foo.py")

    tmp_path.joinpath("jobs").mkdir(parents=True)
    tmp_path.joinpath("jobs/foo.py").touch()

    command = command_tester.command("make job")

    assert command.run("FooJob") == 1

    expected = """\
  - The job file jobs/foo.py already exists.
"""

    assert command.output.fetch() == expected
