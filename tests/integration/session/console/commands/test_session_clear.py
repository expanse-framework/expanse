from typing import TYPE_CHECKING

import time_machine

from whenever import Instant

from expanse.core.application import Application
from expanse.testing.command_tester import CommandTester


if TYPE_CHECKING:
    from expanse.session.session_manager import SessionManager


async def test_command_calls_the_underlying_store_to_clear_expired_sessions(
    app: Application, command_tester: CommandTester
) -> None:
    app.config["session"]["store"] = "dictionary"
    manager: SessionManager = await app.container.get("session:manager")

    store = (await manager.stores())[1]

    command = command_tester.command("session clear")
    return_code = command.run()

    assert return_code == 0
    assert command.output.fetch() == "No expired sessions to clear.\n"

    with time_machine.travel(
        Instant.now().subtract(minutes=180).to_stdlib(), tick=False
    ):
        await store.write("s" * 40, "payload")

    return_code = command.run()
    assert return_code == 0

    assert command.output.fetch() == "Cleared 1 expired sessions\n"
