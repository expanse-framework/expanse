from expanse.console.commands.command import Command
from expanse.schematic.generator import Generator
from expanse.schematic.generator_config import GeneratorConfig


class SchematicExportCommand(Command):
    name = "schematic export"
    description = "Export the OpenAPI document to a JSON file."

    async def handle(
        self, generator: Generator, generator_config: GeneratorConfig
    ) -> None:
        generator.generate(generator_config)
