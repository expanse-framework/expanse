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


class ConsoleFormatter(logging.Formatter):
    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "#5f5fff",
        "INFO": "#5fffd7",
        "WARNING": "#d7ff87",
        "ERROR": "#ff5f87",
        "CRITICAL": "#af5fd7",
        "Exception": "#ff5f87",
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
            for arg_name, arg_value in args.items():
                args[arg_name] = f"<fg=blue>{arg_value}</>"
        elif args:
            args = tuple(f"<options=bold>{arg_value}</>" for arg_value in args)
        else:
            args = ()

        log_message = record.msg % args
        level = record.levelname
        time = pendulum.from_timestamp(record.created, tz="local").format("HH:mm:ss")
        lines = []
        lines.append(
            "".join(
                [
                    f"<options=dark>{time}</> <fg={self.COLORS[level]}>{level[:4]}</> {log_message}",
                ]
            )
        )

        if exception:
            output = BufferedOutput(decorated=True)
            output.set_verbosity(Verbosity.VERY_VERBOSE)
            trace = ExceptionTrace(exception)
            trace.render(output)
            lines.append(output.fetch())

        return self._formatter.format("\n".join(lines))
