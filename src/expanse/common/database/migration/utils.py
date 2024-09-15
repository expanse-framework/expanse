import logging

from typing import TYPE_CHECKING
from typing import ClassVar
from typing import Protocol

from alembic.runtime.migration import RevisionStep


if TYPE_CHECKING:
    from logging import LogRecord

    from cleo.io.io import IO


class Formatter(Protocol):
    def format(self, msg: "LogRecord") -> str | None: ...


class MigrationFormatter:
    def format(self, record: "LogRecord") -> str | None:
        msg = record.msg
        if msg.startswith(("Context impl ", "Will assume ")):
            return None
        elif msg.startswith("Running "):
            assert isinstance(record.args, tuple)
            assert isinstance(record.args[0], RevisionStep)
            # First arg should be the revision step
            step: RevisionStep = record.args[0]
            msg_parts = [
                "  -",
                "<comment>Applying</comment>"
                if step.is_upgrade
                else "<fg=yellow>Rolling back</>",
                "migration",
                f"<info>{step.revision.revision}</info>",
                f"<options=dark>({step.revision.doc})</>",
            ]
            record.args = record.args[1:]
            return " ".join(msg_parts)

        return msg


class IOFormatter(logging.Formatter):
    _colors: ClassVar[dict[str, str]] = {
        "error": "fg=red",
        "warning": "fg=yellow",
        "debug": "debug",
        "info": "fg=blue",
    }

    def __init__(self, formatters: dict[str, Formatter]) -> None:
        super().__init__()

        self._formatters = formatters

    def format(self, record: "LogRecord") -> str:
        if not record.exc_info:
            level = record.levelname.lower()
            msg = record.msg

            if record.name in self._formatters:
                msg = self._formatters[record.name].format(record)
                if msg is None:
                    return ""
            elif level in self._colors:
                msg = f"<{self._colors[level]}>{msg}</>"

            record.msg = msg

        formatted = super().format(record)

        return formatted


class IOHandler(logging.Handler):
    def __init__(self, io: "IO") -> None:
        self._io = io

        super().__init__()

    def emit(self, record: "LogRecord") -> None:
        try:
            msg = self.format(record)
            level = record.levelname.lower()
            err = level in ("warning", "error", "exception", "critical")
            if err:
                self._io.write_error_line(msg)
            elif msg:
                self._io.write_line(msg)
        except Exception:
            self.handleError(record)


def configure_alembic_loggers(io: "IO", disable: bool = False) -> None:
    """
    Configure Alembic loggers so that the output is nicer than the default one.
    """
    logger = logging.getLogger("alembic.runtime.migration")

    if disable:
        for handler in logger.handlers:
            logger.removeHandler(handler)
    else:
        level = logging.INFO
        if io.is_debug():
            level = logging.DEBUG

        handler = IOHandler(io)
        handler.setFormatter(
            IOFormatter({"alembic.runtime.migration": MigrationFormatter()})
        )
        handler.setLevel(level)
        logger.addHandler(handler)
        logger.setLevel(level)
