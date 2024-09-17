import base64
import re

from typing import ClassVar

from cleo.helpers import option
from cleo.io.inputs.option import Option

from expanse.asynchronous.console.commands.command import Command
from expanse.asynchronous.core.application import Application
from expanse.common.encryption.encryptor import Cipher
from expanse.common.encryption.encryptor import Encryptor


class EncryptionKeyGenerateCommand(Command):
    name: str = "encryption key generate"
    description: str = "Generate a new encryption key."

    options: ClassVar[list[Option]] = [
        option(
            "show", None, "Only display the encryption key without modifying files."
        ),
    ]

    async def handle(self, app: Application) -> int:
        raw_key = Encryptor.generate_random_key(
            Cipher(app.config.get("encryption.cipher"))
        )
        key = f"base64:{base64.urlsafe_b64encode(raw_key).decode()}"

        if self.option("show"):
            self.line("")
            self.line(f"<c1>{key}</c1>")

            return 0

        if not await self._replace_key(app, key):
            return 1

        app.config["app.secret_key"] = key

        self.line("Application secret key generated successfully.", style="success")

        return 0

    async def _replace_key(self, app: Application, key: str) -> bool:
        existing_key: str | None = app.config.get("app.secret_key")

        if existing_key and not self.confirm(
            "Do you want to replace the existing application secret key?"
        ):
            return False

        return await self._write_key(app, key)

    async def _write_key(self, app: Application, key: str) -> bool:
        env_file = app.environment_path / app.environment_file
        if not env_file.exists():
            self.line_error("The .env file does not exist.", style="error")

            return False

        content = env_file.read_text()

        escaped = re.escape(f"={app.config.get('app.secret_key', '')}")

        new_content = re.sub(
            rf"^APP_SECRET_KEY{escaped}",
            f"APP_SECRET_KEY={key}",
            content,
            flags=re.MULTILINE,
        )

        if new_content == content:
            self.line_error(
                "The application key could not be set. "
                "Please check your .env file and that a APP_SECRET_KEY is present.",
                style="error",
            )

            return False

        env_file.write_text(new_content)

        return True
