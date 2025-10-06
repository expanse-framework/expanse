import json

from expanse.console.commands.command import Command
from expanse.openapi.generator import OpenAPIGenerator


class OpenapiExportCommand(Command):
    name = "openapi export"
    description = "Export the OpenAPI document to a JSON file."

    async def handle(self, generator: OpenAPIGenerator) -> None:
        print(json.dumps(generator.generate(), indent=2, sort_keys=True))
