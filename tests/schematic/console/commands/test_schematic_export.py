from pathlib import Path

from expanse.core.application import Application
from expanse.schematic.generator_config import GeneratorConfig
from expanse.schematic.schematic_service_provider import SchematicServiceProvider
from expanse.testing.command_tester import CommandTester


async def test_command_exports_to_default_export_path(
    app: Application, tmp_path: Path
) -> None:
    tester = CommandTester(app)

    await SchematicServiceProvider(app.container).register()
    config = await app.container.get(GeneratorConfig)

    tmp_path.joinpath("schematics").mkdir()
    config.set("export_path", str(tmp_path / "schematics" / "api.json"))

    code = tester.command("schematic export").run()
    assert code == 0

    assert (tmp_path / "schematics" / "api.json").is_file()


async def test_command_exports_to_custom_export_path(
    app: Application, tmp_path: Path
) -> None:
    tester = CommandTester(app)

    await SchematicServiceProvider(app.container).register()
    config = await app.container.get(GeneratorConfig)

    tmp_path.joinpath("schematics").mkdir()
    custom_path = tmp_path / "schematics" / "custom_api.json"
    config.set("export_path", str(tmp_path / "api.json"))

    code = tester.command("schematic export").run(f"--path {custom_path}")
    assert code == 0

    assert custom_path.is_file()
