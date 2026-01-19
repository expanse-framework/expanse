import logging

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
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red",
        "Exception": "red",
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

        log_message = super().format(record)
        width = min(self._terminal.width, 80)
        level = record.levelname
        time = pendulum.from_timestamp(record.created, tz="local").format("HH:mm:ss")
        lines = []
        lines.append(
            "".join(
                [
                    f"<options=dark>{self._top_left_marker}</>",
                    f" <options=dark>{time}</> <fg={self.COLORS[level]}>{level}</> ",
                    f"<options=dark>{(width - len(level) - len(time) - 1 - 4) * '─'}</>",
                    f"<options=dark>{self._top_right_marker}</>",
                ]
            )
        )
        lines.append(
            f"<options=dark>{self._vertical_marker}</>"
            f" {log_message} "
            f"{' ' * (width - len(log_message) - 4)}"
            f"<options=dark>{self._vertical_marker}</>"
        )
        lines.append(
            f"<options=dark>{self._bottom_left_marker}{(width - 2) * '─'}{self._bottom_right_marker}</>"
        )

        if exception:
            output = BufferedOutput(decorated=True)
            output.set_verbosity(Verbosity.VERY_VERBOSE)
            trace = ExceptionTrace(exception)
            trace.render(output)
            lines.append(output.fetch())

        return self._formatter.format("\n".join(lines))
