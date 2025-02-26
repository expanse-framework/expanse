from pathlib import Path
from typing import TYPE_CHECKING

from expanse.container.container import Container
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.core.console.gateway import Gateway
    from expanse.encryption.encryptor import Encryptor


class EncryptionServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.encryption.encryptor import Encryptor
        from expanse.encryption.encryptor_factory import EncryptorFactory

        self._container.singleton(EncryptorFactory)
        self._container.singleton(Encryptor, self._create_encryptor)

    async def boot(self) -> None:
        from expanse.core.console.gateway import Gateway

        await self._container.on_resolved(Gateway, self._register_command_path)

    async def _create_encryptor(self, container: Container) -> "Encryptor":
        from expanse.encryption.encryptor_factory import EncryptorFactory

        factory = await container.get(EncryptorFactory)

        return factory.make()

    async def _register_command_path(self, gateway: "Gateway") -> None:
        await gateway.load_path(Path(__file__).parent.joinpath("console/commands"))
