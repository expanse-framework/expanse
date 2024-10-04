from expanse.console.commands.command import Command


class SyncFooBarCommand(Command):
    name = "sync foo bar"

    def handle(self) -> int:
        self.info("Sync foo Bar")

        return 0
