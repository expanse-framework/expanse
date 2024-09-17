from pathlib import Path

from expanse.core.application import Application
from expanse.encryption.console.commands.encryption_key_generate import (
    EncryptionKeyGenerateCommand,  # noqa: F401
)
from expanse.testing.command_tester import CommandTester


def test_generate_key_without_env_file(
    command_tester: CommandTester, app: Application, tmp_path: Path
) -> None:
    app._environment_path = tmp_path

    command = command_tester.command("encryption key generate")

    return_code = command.run()
    assert return_code == 1

    expected = """The .env file does not exist.
"""

    assert command.output.fetch() == expected


def test_generate_key_with_env_file_but_without_app_secret_key(
    command_tester: CommandTester, app: Application, tmp_path: Path
) -> None:
    tmp_path.joinpath(".env").write_text("")
    app._environment_path = tmp_path

    command = command_tester.command("encryption key generate")

    return_code = command.run()
    assert return_code == 1

    expected = """The application key could not be set. \
Please check your .env file and that a APP_SECRET_KEY is present.
"""

    assert command.output.fetch() == expected


def test_generate_key_with_env_file_and_with_empty_app_secret_key(
    command_tester: CommandTester, app: Application, tmp_path: Path
) -> None:
    app.config["app.secret_key"] = ""
    tmp_path.joinpath(".env").write_text("APP_SECRET_KEY=")
    app._environment_path = tmp_path

    command = command_tester.command("encryption key generate")

    return_code = command.run()
    assert return_code == 0

    expected = """Application secret key generated successfully.
"""

    assert command.output.fetch() == expected

    assert app.config["app.secret_key"] != ""
    assert (
        tmp_path.joinpath(".env").read_text().strip()
        == f"APP_SECRET_KEY={app.config['app.secret_key']}"
    )


def test_generate_key_with_env_file_and_with_non_empty_app_secret_key(
    command_tester: CommandTester, app: Application, tmp_path: Path
) -> None:
    app.config["app.secret_key"] = "S" * 32
    tmp_path.joinpath(".env").write_text(f"APP_SECRET_KEY={'S' * 32}")
    app._environment_path = tmp_path

    command = command_tester.command("encryption key generate")

    return_code = command.with_user_input("y\n").run()
    assert return_code == 0

    expected = """Do you want to replace the existing application secret key? (yes/no) [no]\
 Application secret key generated successfully.
"""

    assert command.output.fetch() == expected

    assert app.config["app.secret_key"] != "S" * 32
    assert (
        tmp_path.joinpath(".env").read_text().strip()
        == f"APP_SECRET_KEY={app.config['app.secret_key']}"
    )


def test_generate_key_with_env_file_and_with_non_empty_app_secret_key_and_no_confirmation(
    command_tester: CommandTester, app: Application, tmp_path: Path
) -> None:
    app.config["app.secret_key"] = "S" * 32
    tmp_path.joinpath(".env").write_text(f"APP_SECRET_KEY={'S' * 32}")
    app._environment_path = tmp_path

    command = command_tester.command("encryption key generate")

    return_code = command.with_user_input("n\n").run()
    assert return_code == 1

    expected = (
        "Do you want to replace the existing application secret key? (yes/no) [no] "
    )

    assert command.output.fetch() == expected

    assert app.config["app.secret_key"] == "S" * 32
    assert tmp_path.joinpath(".env").read_text().strip() == f"APP_SECRET_KEY={'S' * 32}"


def test_generate_key_show_only(
    command_tester: CommandTester, app: Application, tmp_path: Path
) -> None:
    command = command_tester.command("encryption key generate")

    return_code = command.run("--show")
    assert return_code == 0

    assert command.output.fetch().strip().startswith("base64:")
