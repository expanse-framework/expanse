from pathlib import Path
from typing import Any

from expanse.common.core.application import Application


class Stub:
    def __init__(self, path: Path) -> None:
        self._path: Path = path

    def generate(self, parameters: dict[str, Any]) -> str:
        content = self._path.read_text()

        return content.format(**parameters)

    def generate_to(self, path: Path, parameters: dict[str, Any]) -> None:
        path.write_text(self.generate(parameters))


class Generator:
    def __init__(self, app: Application) -> None:
        self._app: Application = app

    def stub(self, stub: str) -> Stub:
        path = self.resolve(stub)

        if path is None:
            raise ValueError(f"Stub not found: {stub}")

        return Stub(path)

    def resolve(self, stub: str) -> Path | None:
        paths: list[Path] = [
            self._app.path("stubs"),
            Path(__file__).parent.joinpath("stubs"),
        ]
        for path in paths:
            stub_path = path.joinpath(stub).with_suffix(".stub")
            if stub_path.exists():
                return path.joinpath(stub_path)

        return None
