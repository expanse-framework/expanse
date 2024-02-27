from expanse.console.commands.command import Command


class FooBarCommand(Command):
    name = "foo bar"

    def handle(self) -> int:
        self.info("Foo Bar")

        return 0
