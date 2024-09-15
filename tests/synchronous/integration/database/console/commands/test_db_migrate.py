from pathlib import Path

from expanse.core.application import Application
from expanse.database.console.commands.db_migrate import DbMigrateCommand  # noqa: F401
from expanse.database.database_manager import DatabaseManager
from expanse.testing.command_tester import CommandTester


def test_migrate(
    command_tester: CommandTester, app: Application, tmp_path: Path
) -> None:
    app.config["paths"]["database"] = (
        Path(__file__).parent.joinpath("fixtures").relative_to(app.base_path)
    )
    app.config["database"]["default"] = "test"

    command = command_tester.command("db migrate")

    return_code = command.run()
    assert return_code == 0

    expected = """
  - Applying migration 1234567890 (Auto Migration)
  - Applying migration 1234567891 (Foo Migration)
"""

    assert command.output.fetch() == expected

    with app.container.make(DatabaseManager).connection() as connection:
        result = connection.execute("SELECT * FROM users")
        assert result.fetchall() == [(1, "John", "Doe", "john@doe.com", "true")]


def test_migrate_with_step(
    command_tester: CommandTester, app: Application, tmp_path: Path
) -> None:
    app.config["paths"]["database"] = (
        Path(__file__).parent.joinpath("fixtures").relative_to(app.base_path)
    )
    app.config["database"]["default"] = "test"

    command = command_tester.command("db migrate")

    return_code = command.run("--step 1")
    assert return_code == 0

    expected = """
  - Applying migration 1234567890 (Auto Migration)
"""

    assert command.output.fetch() == expected


def test_migrate_with_dry_run_mode(
    command_tester: CommandTester, app: Application, tmp_path: Path
) -> None:
    app.config["paths"]["database"] = (
        Path(__file__).parent.joinpath("fixtures").relative_to(app.base_path)
    )
    app.config["database"]["default"] = "test"

    command = command_tester.command("db migrate")

    return_code = command.run("--dry-run")
    assert return_code == 0

    expected = """
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 1234567890

CREATE TABLE users (
    id INTEGER NOT NULL, 
    first_name VARCHAR, 
    last_name VARCHAR, 
    email VARCHAR, 
    PRIMARY KEY (id)
);

INSERT INTO users (first_name, last_name, email)
VALUES ('John', 'Doe', 'john@doe.com');

INSERT INTO alembic_version (version_num) VALUES ('1234567890') RETURNING version_num;

-- Running upgrade 1234567890 -> 1234567891

ALTER TABLE users ADD COLUMN active BOOLEAN DEFAULT 'true' NOT NULL;

UPDATE alembic_version SET version_num='1234567891' WHERE alembic_version.version_num = '1234567890';

"""

    assert command.output.fetch() == expected
