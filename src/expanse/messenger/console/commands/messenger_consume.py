import asyncio
import signal

from math import ceil
from typing import ClassVar

from cleo.helpers import argument
from cleo.helpers import option
from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option

from expanse.console.commands.command import Command
from expanse.messenger.worker import Worker
from expanse.support._utils import wait_for_event


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
        option(
            "concurrency",
            "c",
            description="The number of messages to process concurrently.",
            flag=False,
            default=1,
        ),
        option(
            "keep-alive",
            None,
            description="Whether to keep the worker alive by sending periodic keep-alive signals to the transport. This is useful to ensure transports do not redeliver messages while they are being processed.",
            flag=False,
            value_required=False,
        ),
    ]

    async def handle(self, worker: Worker) -> None:
        transport_name: str | None = self.argument("transport")

        loop = asyncio.get_running_loop()
        has_keep_alive = self._io.input.parameter_option("--keep-alive") is not False

        if has_keep_alive:
            keep_alive_interval = int(self.option("keep-alive") or 5)
        else:
            keep_alive_interval = 0

        keep_alive_task: asyncio.Task[None] | None = None
        stop_keep_alive: asyncio.Event = asyncio.Event()

        async def _keep_alive_loop() -> None:
            while not await wait_for_event(
                stop_keep_alive, timeout=keep_alive_interval
            ):
                await worker.keep_alive(ceil(keep_alive_interval * 3 / 2))

        def _shutdown() -> None:
            worker.stop()

            # Remove custom handlers so that a subsequent signal
            # falls back to default behavior (KeyboardInterrupt / termination).
            loop.remove_signal_handler(signal.SIGINT)
            loop.remove_signal_handler(signal.SIGTERM)

            stop_keep_alive.set()

        loop.add_signal_handler(signal.SIGINT, _shutdown)
        loop.add_signal_handler(signal.SIGTERM, _shutdown)

        if keep_alive_interval > 0:
            keep_alive_task = asyncio.ensure_future(_keep_alive_loop())

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

        try:
            await worker.run(
                transport_name=transport_name,
                limit=(
                    int(self.option("limit"))
                    if self.option("limit") is not None
                    else None
                ),
                sleep=int(self.option("sleep")) * 1000,
                concurrency=int(self.option("concurrency")),
            )
        finally:
            if keep_alive_task is not None:
                stop_keep_alive.set()
                await keep_alive_task
