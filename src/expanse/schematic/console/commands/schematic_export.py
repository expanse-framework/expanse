import json

from typing import ClassVar

import anyio

from cleo.helpers import option
from cleo.io.inputs.option import Option

from expanse.console.commands.command import Command
from expanse.contracts.routing.router import Router
from expanse.schematic.generator import Generator
from expanse.schematic.generator_config import GeneratorConfig


class SchematicExportCommand(Command):
    name = "schematic export"
    description = "Export the OpenAPI document to a JSON file."

    options: ClassVar[list[Option]] = [
        option("path", description="The path to the output JSON file.", flag=False),
    ]

    async def handle(
        self, generator: Generator, generator_config: GeneratorConfig, router: Router
    ) -> None:
        path: str = self.option("path")
        if not path:
            path = generator_config.get("export_path")

        doc = generator.generate(generator_config, router)

        await anyio.Path(path).write_text(json.dumps(doc.to_dict(), indent=2))

        self.info(f"OpenAPI document exported to {path}.")
