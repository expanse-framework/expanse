from typing import Any
from typing import ClassVar

from cleo.helpers import option
from cleo.io.inputs.option import Option

from expanse.asynchronous.console.commands.command import Command
from expanse.asynchronous.core.application import Application


class ServeCommand(Command):
    name: str = "serve"

    options: ClassVar[list[Option]] = [
        option("--port", flag=False, default=8000),
        option("watch"),
    ]

    async def handle(self, app: Application) -> int:
        import uvicorn

        log_level: str = "info"
        if self.io.is_verbose():
            log_level = "debug"

        parameters: dict[str, Any] = {
            "port": self.option("port"),
            "interface": "wsgi",
            "log_level": log_level,
            "reload": self.option("watch"),
            "use_colors": self.io.is_decorated(),
        }

        if self.option("watch"):
            parameters["reload_includes"] = [
                app.path(".").as_posix(),
                app.resources_path.joinpath("views").as_posix(),
            ]

        config = uvicorn.Config("app.app:app", **parameters)
        server = uvicorn.Server(config)
        await server.serve()

        return 0
