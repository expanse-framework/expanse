from typing import TYPE_CHECKING

import pendulum

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

    with pendulum.travel_to(pendulum.now("UTC").subtract(minutes=180)):
        await store.write("s" * 40, "payload")

    return_code = command.run()
    assert return_code == 0

    assert command.output.fetch() == "Cleared 1 expired sessions\n"
