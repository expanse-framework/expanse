from typing import ClassVar

from cleo.helpers import argument
from cleo.io.inputs.argument import Argument

from expanse.console.commands.command import Command
from expanse.messenger.worker import Worker


class MessengerConsumeCommand(Command):
    """
    Consume messages from transports.
    """

    name: str = "messenger consume"

    arguments: ClassVar[list[Argument]] = [
        argument(
            "transport",
            description="The name of the transport to consume from. If not provided, the default transport will be used.",
            optional=True,
        )
    ]

    async def handle(self, worker: Worker) -> None:
        transport_name: str | None = self.argument("transport")

        # Register a shutdown handler to gracefully stop the worker on termination signals
        self._register_shutdown_handler(worker)

        await worker.run(transport_name=transport_name)

    def _register_shutdown_handler(self, worker: Worker) -> None:
        import signal

        signal.signal(signal.SIGINT, lambda sig, frame: worker.stop())
        signal.signal(signal.SIGTERM, lambda sig, frame: worker.stop())
