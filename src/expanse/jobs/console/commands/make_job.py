from typing import TYPE_CHECKING
from typing import ClassVar

from cleo.helpers import argument
from cleo.helpers import option
from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option
from inflection import camelize
from inflection import underscore

from expanse.console.commands.command import Command
from expanse.core.application import Application
from expanse.stubs.generator import Generator


if TYPE_CHECKING:
    from pathlib import Path


class MakeJobCommand(Command):
    name: str = "make job"

    description: str = "Create a new job file."

    arguments: ClassVar[list[Argument]] = [argument("name", "The name of the job.")]

    options: ClassVar[list[Option]] = [option("sync", "s", "Create a synchronous job.")]

    async def handle(self, app: Application, generator: Generator) -> int:
        jobs_path: Path = app.path("jobs")
        if not jobs_path.exists():
            jobs_path.mkdir(parents=True)
            jobs_path.joinpath("__init__.py").touch()

        job_name: str = self.argument("name")
        job_name = camelize(job_name).removesuffix("Job")
        module_name = underscore(job_name)
        job_name = f"{job_name}Job"

        stub_name = "jobs/sync_job" if self.option("sync") else "jobs/job"
        stub = generator.stub(stub_name)

        if jobs_path.joinpath(f"{module_name}.py").exists():
            self.line(
                f"  - <warning>The job file <c1>{app.path(f'jobs/{module_name}.py', relative=True)}</c1> already exists.</warning>"
            )

            return 1

        stub.generate_to(
            jobs_path.joinpath(f"{module_name}.py"),
            {"name": job_name},
        )

        self.line("")
        self.line(
            f"  - Generated file: <c1>{app.path(f'jobs/{module_name}.py', relative=True)}</c1>"
        )

        return 0
