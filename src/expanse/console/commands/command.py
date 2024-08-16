from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import TypeVar

from cleo.exceptions import CleoError
from cleo.io.inputs.string_input import StringInput
from cleo.io.null_io import NullIO

from expanse.common.console.command import Command as BaseCommand


if TYPE_CHECKING:
    from cleo.io.io import IO

    from expanse.console.application import Application  # noqa: TID
    from expanse.core.application import Application as Expanse

TApplication = TypeVar("TApplication", bound="Application")


class Command(BaseCommand[TApplication], ABC):
    def __init__(self) -> None:
        super().__init__()

        self._expanse: Expanse | None = None

    @abstractmethod
    def handle(self, *args, **kwargs) -> int | None: ...

    def run(self, io: IO) -> int:
        self.merge_application_definition()

        try:
            io.input.bind(self.definition)
        except CleoError:
            if not self._ignore_validation_errors:
                raise

        if io.input.has_argument("command") and io.input.argument("command") is None:
            io.input.set_argument("command", self.name)

        io.input.validate()

        status_code = self.execute(io)

        if status_code is None:
            status_code = 0

        return status_code

    def execute(self, io: IO) -> int | None:
        self._io = io

        try:
            if not self._expanse:
                return self.handle()

            return self._expanse.call(self.handle)
        except KeyboardInterrupt:
            return 1

    def set_expanse(self, expanse: Expanse) -> None:
        self._expanse = expanse

    def call(self, name: str, args: str | None = None) -> int:
        """
        Call another command.
        """
        if args is None:
            args = ""

        input = StringInput(args)
        assert self.application is not None
        command = self.application.get(name)

        return self.application._run_command(command, self._io.with_input(input))

    def call_silent(self, name: str, args: str | None = None) -> int:
        """
        Call another command silently.
        """
        if args is None:
            args = ""

        input = StringInput(args)
        assert self.application is not None
        command = self.application.get(name)

        return self.application._run_command(command, NullIO(input))
