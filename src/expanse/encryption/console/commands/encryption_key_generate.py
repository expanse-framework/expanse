import base64
import re

from typing import ClassVar

from cleo.helpers import option
from cleo.io.inputs.option import Option

from expanse.console.commands.command import Command
from expanse.core.application import Application
from expanse.encryption.encryptor import Cipher
from expanse.encryption.encryptor import Encryptor


KEYS: dict[str, dict[str, str]] = {
    "key": {"var": "APP_SECRET_KEY", "config": "app.secret_key"},
    "salt": {"var": "ENCRYPTION_SALT", "config": "encryption.salt"},
}


class EncryptionKeyGenerateCommand(Command):
    name: str = "encryption key generate"
    description: str = "Generate a new encryption key."

    options: ClassVar[list[Option]] = [
        option("key", None, "Generate the secret key."),
        option("salt", None, "Generate the encryption salt."),
        option(
            "show", None, "Only display the encryption key without modifying files."
        ),
    ]

    async def handle(self, app: Application) -> int:
        if self.option("key") or self.option("salt"):
            key_names = [key for key in KEYS if self.option(key)]
        else:
            key_names = list(KEYS.keys())

        for key_name in key_names:
            result = await self._generate_key(app, key_name)

            if result != 0:
                return result

        return 0

    async def _generate_key(self, app: Application, key_name: str) -> int:
        raw_key = Encryptor.generate_random_key(
            Cipher(app.config.get("encryption.cipher"))
        )
        key = f"base64:{base64.urlsafe_b64encode(raw_key).decode()}"

        if self.option("show"):
            self.line("")
            self.line(f"<c1>{key}</c1>")

            return 0

        if not await self._replace_key(app, key, key_name):
            return 1

        app.config[KEYS[key_name]["config"]] = key

        self.line(f"Application {key_name} generated successfully.", style="success")

        return 0

    async def _replace_key(self, app: Application, key: str, key_name: str) -> bool:
        existing_key: str | None = app.config.get(KEYS[key_name]["config"], raw=True)

        if existing_key and not self.confirm(
            f"Do you want to replace the existing application {key_name}?"
        ):
            return False

        return await self._write_key(app, key, key_name)

    async def _write_key(self, app: Application, key: str, key_name: str) -> bool:
        env_file = app.environment_path / app.environment_file
        if not env_file.exists():
            self.line_error("The .env file does not exist.", style="error")

            return False

        content = env_file.read_text()

        escaped = re.escape(
            f"={app.config.get(KEYS[key_name]['config'], '', raw=True)}"
        )

        new_content = re.sub(
            rf"^{KEYS[key_name]['var']}{escaped}",
            f"{KEYS[key_name]['var']}={key}",
            content,
            flags=re.MULTILINE,
        )

        if new_content == content:
            self.line_error(
                f"The application {key_name} could not be set. "
                f"Please check your .env file and that a {KEYS[key_name]['var']} is present.",
                style="error",
            )

            return False

        env_file.write_text(new_content)

        return True
