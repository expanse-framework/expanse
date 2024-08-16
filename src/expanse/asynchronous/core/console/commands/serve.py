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
        if self._io.is_verbose():
            log_level = "debug"
        elif self._io.output.is_quiet():
            log_level = "error"

        parameters: dict[str, Any] = {
            "port": int(self.option("port")),
            "log_level": log_level,
            "reload": self.option("watch"),
            "use_colors": self._io.is_decorated(),
        }

        if self.option("watch"):
            parameters["reload_dirs"] = [
                app.base_path,
                app.config_path,
                app.base_path.joinpath("routes"),
            ]

        config = uvicorn.Config("app.app:app", **parameters)
        server = uvicorn.Server(config)

        if self.option("watch"):
            from uvicorn.supervisors import ChangeReload

            sock = config.bind_socket()
            ChangeReload(config, target=server.run, sockets=[sock]).run()
        else:
            await server.serve()

        return 0
