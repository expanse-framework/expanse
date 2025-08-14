import pytest

from expanse.core.application import Application
from expanse.database.asynchronous.database_manager import AsyncDatabaseManager
from expanse.queue.asynchronous.queues.database_queue import AsyncDatabaseQueue
from expanse.testing.command_tester import CommandTester


def simple_job() -> None:
    pass


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_jobs_can_be_put_in_the_queue(
    app: Application, command_tester: CommandTester, name: str
) -> None:
    app.config["database"]["default"] = name

    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    queue = AsyncDatabaseQueue(db.connection(name), "jobs")

    await queue.put(simple_job, data="test_data")
