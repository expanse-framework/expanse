import asyncio
import signal

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

        loop = asyncio.get_running_loop()

        def _shutdown() -> None:
            worker.stop()

            # Remove custom handlers so that a subsequent signal
            # falls back to default behavior (KeyboardInterrupt / termination).
            loop.remove_signal_handler(signal.SIGINT)
            loop.remove_signal_handler(signal.SIGTERM)

        loop.add_signal_handler(signal.SIGINT, _shutdown)
        loop.add_signal_handler(signal.SIGTERM, _shutdown)

        await worker.run(transport_name=transport_name)
