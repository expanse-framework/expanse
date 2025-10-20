import json

from expanse.console.commands.command import Command
from expanse.contracts.routing.router import Router
from expanse.schematic.generator import Generator
from expanse.schematic.generator_config import GeneratorConfig


class SchematicExportCommand(Command):
    name = "schematic export"
    description = "Export the OpenAPI document to a JSON file."

    async def handle(
        self, generator: Generator, generator_config: GeneratorConfig, router: Router
    ) -> None:
        print(
            json.dumps(generator.generate(generator_config, router).to_dict(), indent=2)
        )
