import re

from argparse import Namespace
from collections.abc import Iterator
from contextlib import contextmanager
from contextlib import suppress
from pathlib import Path

from alembic import util
from alembic.command import downgrade
from alembic.command import init
from alembic.command import revision
from alembic.command import upgrade
from cleo.io.io import IO
from cleo.io.null_io import NullIO
from cleo.ui.progress_indicator import ProgressIndicator

from expanse.common.core.application import Application
from expanse.common.database.migration.config import Config as AlembicConfig
from expanse.common.database.migration.utils import configure_alembic_loggers


class Buffer:
    def __init__(self, io: IO) -> None:
        from pygments.formatters import TerminalFormatter
        from pygments.lexers import get_lexer_by_name

        self._io = io
        self._output = io.output
        self._lexer = get_lexer_by_name("sql", stripnl=False)
        self._formatter = TerminalFormatter()

    def write(self, data: str) -> int:
        if self._should_filter_message(data):
            return 0

        data = self._format(data)
        self._io.write(data)

        return len(data)

    def read(self, size: int = -1) -> str:
        return self._io.read(size)

    def flush(self) -> None:
        self._io.flush()

    def isatty(self) -> bool:
        return False

    def seekable(self) -> bool:
        return False

    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return True

    def close(self) -> None:
        self.flush()

    def _format(self, data: str) -> str:
        if not self._io.is_decorated():
            return data

        from pygments import highlight

        return highlight(data, self._lexer, self._formatter)

    def _should_filter_message(self, message: str) -> bool:
        if message == "Generating static SQL":
            return True

        return False


class Migrator:
    def __init__(self, app: Application) -> None:
        self._app: Application = app
        self._config = AlembicConfig(app, cmd_opts=Namespace(quiet=True))

    @property
    def config(self) -> AlembicConfig:
        return self._config

    def init(self, io: IO | None = None) -> None:
        if io is None:
            io = NullIO()

        path = self._app.named_path("database").joinpath("migrations")
        with suppress(ValueError):
            path = path.relative_to(self._app.base_path)

        with self._patched_status(io):
            init(
                self._config,
                str(path),
                template="default",
            )

    def make(
        self, message: str | None = None, auto: bool = False, *, io: IO | None = None
    ) -> None:
        if io is None:
            io = NullIO()

        migration_directory = self._app.named_path("database").joinpath("migrations")

        if not migration_directory.exists():
            self.init(io=io)

        if auto:
            # If the migration should be auto-generated, load the models first
            # to ensure that alembic sees all the model changes.
            # This is not done in the Alembic's env.py file to avoid loading
            # models unnecessarily.
            self._load_models()

        with self._patched_status(io):
            revision(self._config, message=message, autogenerate=auto)

    def migrate(
        self, revision: str = "head", dry_run: bool = False, *, io: IO | None = None
    ) -> None:
        if io is None:
            io = NullIO()

        if dry_run:
            configure_alembic_loggers(io, disable=True)
            self._config.output_buffer = Buffer(io)  # type: ignore[assignment]

        upgrade(self._config, revision, sql=dry_run)

    def rollback(self, revision: str = "-1", *, io: IO | None = None) -> None:
        if io is None:
            io = NullIO()

        downgrade(self._config, revision)

    def _load_models(self) -> None:
        model_directory = self._app.path("models")
        for path in model_directory.rglob("*.py"):
            if path.stem.startswith("_"):
                continue

            from importlib import import_module

            path = path.relative_to(self._app.base_path)
            module_name = path.with_suffix("").as_posix().replace("/", ".")
            import_module(module_name)

    @contextmanager
    def _indicator(
        self,
        io: IO,
        start_message: str,
        end_message: str,
        fmt: str = "{message}",
    ) -> Iterator[None]:
        indicator = ProgressIndicator(io, fmt)

        with indicator.auto(start_message, end_message):
            yield

    @contextmanager
    def _patched_status(self, io: IO) -> Iterator[None]:
        @contextmanager
        def status(
            status_msg: str, newline: bool = False, quiet: bool = False
        ) -> Iterator[None]:
            if status_msg.startswith("Generating "):
                try:
                    path = Path(status_msg[11:]).relative_to(self._app.base_path)
                    status_msg = f"Generating <c1>{path}</c1>"
                except Exception:
                    pass
            elif status_msg.startswith("Creating directory "):
                try:
                    if m := re.match(r"Creating directory '([^']+)'", status_msg):
                        try:
                            path = Path(m.group(1)).relative_to(self._app.base_path)
                        except ValueError:
                            # The path is not relative to the base path
                            # Most likely due to being run in tests
                            path = Path(m.group(1))

                        status_msg = f"Creating directory <c1>{path}</c1>"
                except Exception:
                    pass

            status_msg = f"{status_msg}..."

            with self._indicator(
                io,
                status_msg,
                status_msg + " <success>Done</success>",
                fmt="  - {message}",
            ):
                yield

        original_status = util.status
        util.status = status

        yield

        util.status = original_status
