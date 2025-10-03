from pathlib import Path
from typing import TYPE_CHECKING

from expanse.configuration.config import Config
from expanse.core.console.portal import Portal
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.schematic.generator_config import GeneratorConfig


class SchematicServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.schematic.generator_config import GeneratorConfig

        await self._container.on_resolved(Portal, self.register_commands)

        self._container.singleton(GeneratorConfig, self.create_config)

    async def create_config(self, config: Config) -> "GeneratorConfig":
        from expanse.schematic.generator_config import GeneratorConfig

        generator_config = GeneratorConfig(config["schematic"])

        return generator_config

    async def register_commands(self, portal: Portal) -> None:
        portal = await self._container.get(Portal)
        await portal.load_path(Path(__file__).parent.joinpath("console/commands"))
