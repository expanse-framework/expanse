import asyncio
import signal

from typing import ClassVar

from cleo.helpers import argument
from cleo.helpers import option
from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option

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

    options: ClassVar[list[Option]] = [
        option(
            "limit",
            None,
            description="The maximum number of messages to consume before stopping.",
            flag=False,
        ),
        option(
            "sleep",
            None,
            description="The number of seconds to sleep between polling for messages when no messages are available.",
            flag=False,
            default=1,
        ),
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

        stop_conditions: list[str] = []
        if self.option("limit") is not None:
            stop_conditions.append(
                f"after consuming <info>{self.option('limit')}</info> messages"
            )

        self.line_error(
            f"Consuming messages from the <success>{transport_name or 'default'}</success> transport"
        )

        if stop_conditions:
            stop_conditions_message = " or ".join(stop_conditions)
            self.line_error(
                f"<comment>The worker will stop {stop_conditions_message}.</comment>"
            )

        self.line_error("<comment>Press Ctrl+C to stop consuming messages.</comment>")

        await worker.run(
            transport_name=transport_name,
            limit=(
                int(self.option("limit")) if self.option("limit") is not None else None
            ),
            sleep=int(self.option("sleep")) * 1000,
        )
