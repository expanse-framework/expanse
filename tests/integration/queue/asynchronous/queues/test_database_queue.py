import json

import pytest

from sqlalchemy.orm import Session

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
    app.container.instance(Session, db.session(name))
    queue = AsyncDatabaseQueue(db, name, "jobs").set_container(app.container)

    await queue.put(simple_job, data="test_data")

    async with db.connection(name) as conn:
        result = (await conn.execute("SELECT * FROM jobs")).fetchall()
        assert len(result) == 1
        payload = json.loads(result[0].payload)
        assert "id" in payload
        assert payload["data"] == "test_data"
        assert payload["display_name"] == "simple_job"
        assert payload["job"] == [
            "tests.integration.queue.asynchronous.queues.test_database_queue",
            "simple_job",
        ]
        assert result[0].queue == "default"


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_size_of_queue_can_be_computed(
    app: Application, command_tester: CommandTester, name: str
) -> None:
    app.config["database"]["default"] = name

    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    app.container.instance(Session, db.session(name))
    queue = AsyncDatabaseQueue(db, name, "jobs").set_container(app.container)

    await queue.put(simple_job, data="test_data")
    await queue.put(simple_job, queue="jobs2")
    await queue.put(simple_job, queue="jobs2")

    assert await queue.size() == 1
    assert await queue.size("jobs2") == 2
