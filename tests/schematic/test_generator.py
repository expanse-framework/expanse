import json

from pathlib import Path

import pytest

from expanse.core.application import Application
from expanse.routing.router import Router
from expanse.schematic.generator import Generator
from expanse.schematic.generator_config import GeneratorConfig
from expanse.schematic.inference.inference import Inference
from expanse.schematic.schematic_service_provider import SchematicServiceProvider
from expanse.schematic.support.operation_builder import OperationBuilder


@pytest.mark.parametrize(
    "fixture",
    ["basic_routes", "typed_routes", "typed_routes_with_doc", "routes_with_inference"],
)
async def test_generated_schema(unbootstrapped_app: Application, fixture: str) -> None:
    container = unbootstrapped_app.container
    route_file = Path(__file__).parent / "fixtures" / fixture / "routes.py"
    schema_file = Path(__file__).parent / "fixtures" / fixture / "schema.json"
    router = Router()
    with router.group("api", prefix="/api") as group:
        group.load_file(route_file)

    config = GeneratorConfig()
    config.set("api_path", "/api")
    config.set("title", "Test API")
    config.set("info.version", "1.0.0")
    config.set("info.description", "This is a test API.")

    await SchematicServiceProvider(container).register()

    generator = Generator(
        await container.get(OperationBuilder), await container.get(Inference)
    )

    json.dumps(json.loads(schema_file.read_text()), indent=2, sort_keys=True)
    assert generator.generate(config, router).to_dict() == json.loads(
        schema_file.read_text()
    )
