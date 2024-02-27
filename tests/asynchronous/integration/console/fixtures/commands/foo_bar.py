from expanse.asynchronous.console.commands.command import Command


class FooBarCommand(Command):
    name = "foo bar"

    async def handle(self) -> int:
        self.info("Foo Bar")

        return 0
