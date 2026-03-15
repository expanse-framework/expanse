import logging

from collections.abc import Mapping
from typing import ClassVar
from typing import Literal

import pendulum

from cleo.formatters.formatter import Formatter
from cleo.io.outputs.buffered_output import BufferedOutput
from cleo.io.outputs.output import Verbosity
from cleo.terminal import Terminal
from cleo.ui.exception_trace import ExceptionTrace


RESERVED_ATTRS: set[str] = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class ConsoleFormatter(logging.Formatter):
    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "#5f87ff",
        "INFO": "#5fd7ff",
        "WARNING": "#ffd700",
        "ERROR": "#ff5f5f",
        "CRITICAL": "#d75fff",
        "Exception": "#ff5f5f",
    }

    def __init__(
        self,
        style: Literal["%", "{", "$"] = "%",
        validate: bool = True,
        *,
        defaults=None,
    ) -> None:
        super().__init__(fmt="%(message)s", style="%")

        self._formatter = Formatter(decorated=True)
        self._terminal = Terminal()
        self._top_left_marker = "┌"
        self._top_right_marker = "┐"
        self._bottom_left_marker = "└"
        self._bottom_right_marker = "┘"
        self._vertical_marker = "│"

    def format(self, record: logging.LogRecord) -> str:
        exception: BaseException | None = None
        if record.exc_info:
            exception = record.exc_info[1]
            record.exc_info = None

        args = record.args
        if isinstance(args, Mapping):
            args = {
                arg_name: f"<fg=blue>{arg_value}</>"
                for arg_name, arg_value in args.items()
            }
        elif args:
            args = tuple(f"<options=bold>{arg_value}</>" for arg_value in args)
        else:
            args = ()

        log_message = str(record.msg) % args
        level = record.levelname
        time = pendulum.from_timestamp(record.created, tz="local").format("HH:mm:ss")
        lines = []
        lines.append(
            "".join(
                [
                    f"<options=dark>{time}</> <fg={self.COLORS[level]};options=bold>{level[:4]}</> {log_message}",
                ]
            )
        )

        extra = {k: v for k, v in record.__dict__.items() if k not in RESERVED_ATTRS}
        if extra:
            lines.extend([f"  <options=bold>{k}</>: {v}" for k, v in extra.items()])

        if exception and isinstance(exception, Exception):
            output = BufferedOutput(decorated=True)
            output.set_verbosity(Verbosity.VERY_VERBOSE)
            trace = ExceptionTrace(exception)
            trace.render(output)
            lines.append(output.fetch())

        return self._formatter.format("\n".join(lines))
