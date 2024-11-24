from typing import TYPE_CHECKING

from expanse.console.commands.command import Command
from expanse.container.container import Container


if TYPE_CHECKING:
    from expanse.session.session_manager import SessionManager


class SessionClearCommand(Command):
    name: str = "session clear"
    description: str = "Clear the expired sessions."

    async def handle(self, container: Container) -> int:
        manager: SessionManager = await container.get("session:manager")
        stores = await manager.stores()
        store = stores[1]

        cleared = await store.clear()

        if not cleared:
            self.line("No expired sessions to clear.")
            return 0

        self.line(f"Cleared <success>{cleared}</success> expired sessions")

        return 0
