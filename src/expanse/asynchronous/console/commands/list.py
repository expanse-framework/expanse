from __future__ import annotations

from typing import ClassVar

from cleo.io.inputs.argument import Argument

from expanse.asynchronous.console.commands.command import Command


class ListCommand(Command):
    name = "list"

    description = "Lists commands."

    help = """\
The <info>{command_name}</info> command lists all commands:

  <info>{command_full_name}</info>

You can also display the commands for a specific namespace:

  <info>{command_full_name} test</info>
"""

    arguments: ClassVar[list[Argument]] = [
        Argument("namespace", required=False, description="The namespace name")
    ]

    async def handle(self) -> int:
        from cleo.descriptors.text_descriptor import TextDescriptor

        descriptor = TextDescriptor()
        descriptor._io = self._io

        descriptor._describe_application(
            self._console,  # type: ignore[arg-type]
            namespace=self.argument("namespace"),
        )

        return 0
