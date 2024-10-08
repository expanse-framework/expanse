from __future__ import annotations

import os
import re
import shutil
import sys

from contextlib import suppress
from typing import TYPE_CHECKING
from typing import cast

from cleo.exceptions import CleoCommandNotFoundError
from cleo.exceptions import CleoError
from cleo.exceptions import CleoLogicError
from cleo.exceptions import CleoNamespaceNotFoundError
from cleo.exceptions import CleoUserError
from cleo.formatters.style import Style
from cleo.io.inputs.argument import Argument
from cleo.io.inputs.argv_input import ArgvInput
from cleo.io.inputs.definition import Definition
from cleo.io.inputs.option import Option
from cleo.io.io import IO
from cleo.io.outputs.output import Verbosity
from cleo.io.outputs.stream_output import StreamOutput
from cleo.ui.ui import UI

from expanse.__version__ import __version__
from expanse.console.command_loader import CommandLoader
from expanse.console.commands.help import HelpCommand
from expanse.console.commands.list import ListCommand


if TYPE_CHECKING:
    from cleo.io.inputs.input import Input
    from cleo.io.outputs.output import Output
    from crashtest.solution_providers.solution_provider_repository import (
        SolutionProviderRepository,
    )

    from expanse.console.commands.command import Command
    from expanse.core.application import Application


class Console:
    def __init__(self, app: Application) -> None:
        self._app: Application = app
        self._name = "Beam"
        self._version = __version__
        self._display_name: str | None = None
        self._terminal = shutil.get_terminal_size()
        self._default_command = "list"
        self._single_command = False
        self._want_helps = False
        self._definition: Definition | None = None
        self._catch_exceptions = True
        self._auto_exit = True
        self._initialized = False
        self._ui: UI | None = None

        self._command_loader: CommandLoader = CommandLoader({})
        self._solution_provider_repository: SolutionProviderRepository | None = None

        self._commands: dict[str, Command] = {}
        self._running_command: Command | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def display_name(self) -> str:
        if self._display_name is None:
            return re.sub(r"[\s\-_]+", " ", self._name).title()

        return self._display_name

    @property
    def version(self) -> str:
        return self._version

    @property
    def long_version(self) -> str:
        if self._name:
            if self._version:
                return f"<b>{self.display_name}</b> (version <c1>{self._version}</c1>)"

            return f"<b>{self.display_name}</b>"

        return "<b>Console</b> application"

    @property
    def definition(self) -> Definition:
        if self._definition is None:
            self._definition = self._default_definition

        if self._single_command:
            definition = self._definition
            definition.set_arguments([])

            return definition

        return self._definition

    @property
    def default_commands(self) -> list[Command]:
        return [HelpCommand(), ListCommand()]

    @property
    def help(self) -> str:
        return self.long_version

    @property
    def ui(self) -> UI:
        if self._ui is None:
            self._ui = self._get_default_ui()

        return self._ui

    @property
    def command_loader(self) -> CommandLoader:
        return self._command_loader

    def set_name(self, name: str) -> None:
        self._name = name

    def set_display_name(self, display_name: str) -> None:
        self._display_name = display_name

    def set_version(self, version: str) -> None:
        self._version = version

    def set_ui(self, ui: UI) -> None:
        self._ui = ui

    def set_command_loader(self, command_loader: CommandLoader) -> None:
        self._command_loader = command_loader

    def auto_exits(self, auto_exits: bool = True) -> None:
        self._auto_exit = auto_exits

    def is_auto_exit_enabled(self) -> bool:
        return self._auto_exit

    def are_exceptions_caught(self) -> bool:
        return self._catch_exceptions

    def catch_exceptions(self, catch_exceptions: bool = True) -> None:
        self._catch_exceptions = catch_exceptions

    def is_single_command(self) -> bool:
        return self._single_command

    def set_solution_provider_repository(
        self, solution_provider_repository: SolutionProviderRepository
    ) -> None:
        self._solution_provider_repository = solution_provider_repository

    def add(self, command: Command) -> Command | None:
        self._init()

        command.set_console(self)

        if not command.enabled:
            command.set_console()

            return None

        if not command.name:
            raise CleoLogicError(
                f'The command "{command.__class__.__name__}" cannot have an empty name'
            )

        self._commands[command.name] = command

        for alias in command.aliases:
            self._commands[alias] = command

        return command

    def get(self, name: str) -> Command:
        self._init()

        if not self.has(name):
            raise CleoCommandNotFoundError(name)

        if name not in self._commands:
            # The command was registered in a different name in the command loader
            raise CleoCommandNotFoundError(name)

        command = self._commands[name]

        if self._want_helps:
            self._want_helps = False

            return self.get_help_command(command)

        return command

    def has(self, name: str) -> bool:
        self._init()

        if name in self._commands:
            return True

        if not self._command_loader:
            return False

        return bool(
            self._command_loader.has(name) and self.add(self._command_loader.get(name))
        )

    def get_namespaces(self) -> list[str]:
        namespaces = []
        seen = set()

        for command in self.all().values():
            if command.hidden or not command.name:
                continue

            for namespace in self._extract_all_namespaces(command.name):
                if namespace in seen:
                    continue

                namespaces.append(namespace)
                seen.add(namespace)

            for alias in command.aliases:
                for namespace in self._extract_all_namespaces(alias):
                    if namespace in seen:
                        continue

                    namespaces.append(namespace)
                    seen.add(namespace)

        return namespaces

    def find_namespace(self, namespace: str) -> str:
        all_namespaces = self.get_namespaces()

        if namespace not in all_namespaces:
            raise CleoNamespaceNotFoundError(namespace, all_namespaces)

        return namespace

    def find(self, name: str) -> Command:
        self._init()

        if self.has(name):
            return self.get(name)

        all_commands = []
        if self._command_loader:
            all_commands += self._command_loader.names

        all_commands += [
            name for name, command in self._commands.items() if not command.hidden
        ]

        raise CleoCommandNotFoundError(name, all_commands)

    def all(self, namespace: str | None = None) -> dict[str, Command]:
        self._init()

        if namespace is None:
            commands = self._commands.copy()
            if not self._command_loader:
                return commands

            for name in self._command_loader.names:
                if name not in commands and self.has(name):
                    commands[name] = self.get(name)

            return commands

        commands = {}

        for name, command in self._commands.items():
            if namespace == self.extract_namespace(name, name.count(" ") + 1):
                commands[name] = command

        if self._command_loader:
            for name in self._command_loader.names:
                if (
                    name not in commands
                    and namespace == self.extract_namespace(name, name.count(" ") + 1)
                    and self.has(name)
                ):
                    commands[name] = self.get(name)

        return commands

    async def run(
        self,
        input: Input | None = None,
        output: Output | None = None,
        error_output: Output | None = None,
    ) -> int:
        try:
            io = self.create_io(input, output, error_output)

            self._configure_io(io)

            try:
                exit_code = await self._run(io)
            except BrokenPipeError:
                # If we are piped to another process, it may close early and send a
                # SIGPIPE: https://docs.python.org/3/library/signal.html#note-on-sigpipe
                devnull = os.open(os.devnull, os.O_WRONLY)
                os.dup2(devnull, sys.stdout.fileno())
                exit_code = 0
            except Exception as e:
                if not self._catch_exceptions:
                    raise

                self.render_error(e, io)

                exit_code = 1
                # TODO: Custom error exit codes
        except KeyboardInterrupt:
            exit_code = 1

        if self._auto_exit:
            sys.exit(exit_code)

        return exit_code

    def get_help_command(self, command: Command) -> Command:
        help_command: HelpCommand = cast(HelpCommand, self.get("help"))
        help_command.set_command(command)

        return help_command

    async def _run(self, io: IO) -> int:
        if io.input.has_parameter_option(["--version", "-V"], True):
            io.write_line(self.long_version)

            return 0

        self._setup_command(io)

        assert self._running_command is not None

        exit_code = await self._run_command(self._running_command, io)
        self._running_command = None

        return exit_code

    async def _run_command(self, command: Command, io: IO) -> int:
        async with self._app.container.create_scoped_container() as container:
            command.set_container(container)

            return await command.run(io)

    def _setup_command(self, io: IO) -> None:
        definition = self.definition
        input_definition = Definition()
        for argument in definition.arguments:
            if argument.name == "command":
                argument = Argument(
                    "command",
                    required=True,
                    is_list=True,
                    description=definition.argument("command").description,
                )

            input_definition.add_argument(argument)

        input_definition.set_options(definition.options)

        # Errors must be ignored, full binding/validation
        # happens later when the command is known.
        with suppress(CleoError):
            # Makes ArgvInput.first_argument() able to
            # distinguish an option from an argument.
            io.input.bind(input_definition)

        name = self._get_command_name(io)
        if io.input.has_parameter_option(["--help", "-h"], True):
            if not name:
                name = "help"
                io.set_input(ArgvInput(["console", "help", self._default_command]))
            else:
                self._want_helps = True

        if not name:
            name = self._default_command
            definition = self.definition
            arguments = definition.arguments
            if not definition.has_argument("command"):
                arguments.append(
                    Argument(
                        "command",
                        required=False,
                        description=definition.argument("command").description,
                        default=name,
                    )
                )
            definition.set_arguments(arguments)

        self._running_command = None
        command = self.find(name)

        self._running_command = command

        if " " in name and isinstance(io.input, ArgvInput):
            # If the command is namespaced we rearrange
            # the input to parse it as a single argument
            argv = io.input._tokens[:]

            start: int = 0
            if io.input.script_name is not None:
                argv.insert(0, io.input.script_name)
                start = 1

            namespace = name.split(" ")[:-1]
            index = None
            for i, arg in enumerate(argv):
                if i < start:
                    continue

                if namespace and arg == namespace[0] and len(namespace) == 1:
                    argv[i] = name
                    index = i if index is None else index
                    break
                elif namespace and arg == namespace[0]:
                    namespace.pop(0)
                    index = i

            if index is not None:
                del argv[index + 1 : index + name.count(" ") + start]

            stream = io.input.stream
            interactive = io.input.is_interactive()
            io.set_input(ArgvInput(argv))
            io.input.set_stream(stream)
            io.input.interactive(interactive)

    def create_io(
        self,
        input: Input | None = None,
        output: Output | None = None,
        error_output: Output | None = None,
    ) -> IO:
        if input is None:
            input = ArgvInput()
            input.set_stream(sys.stdin)

        if output is None:
            output = StreamOutput(sys.stdout)

        if error_output is None:
            error_output = StreamOutput(sys.stderr)

        io = IO(input, output, error_output)

        # Set our own CLI styles
        formatter = io.output.formatter
        formatter.set_style("c1", Style("cyan"))
        formatter.set_style("c2", Style("default", options=["bold"]))
        formatter.set_style("info", Style("blue"))
        formatter.set_style("comment", Style("green"))
        formatter.set_style("warning", Style("yellow"))
        formatter.set_style("debug", Style("default", options=["dark"]))
        formatter.set_style("success", Style("green"))

        return io

    def render_error(self, error: Exception, io: IO) -> None:
        from cleo.ui.exception_trace import ExceptionTrace

        trace = ExceptionTrace(
            error, solution_provider_repository=self._solution_provider_repository
        )
        simple = not io.is_verbose() or isinstance(error, CleoUserError)
        trace.render(io.error_output, simple)

    def _configure_io(self, io: IO) -> None:
        if io.input.has_parameter_option("--ansi", True):
            io.decorated(True)
        elif io.input.has_parameter_option("--no-ansi", True):
            io.decorated(False)

        if io.input.has_parameter_option(["--no-interaction", "-n"], True) or (
            io.input._interactive is None
            and io.input.stream
            and not io.input.stream.isatty()
        ):
            io.interactive(False)

        shell_verbosity = int(os.getenv("SHELL_VERBOSITY", 0))
        if shell_verbosity == -1:
            io.set_verbosity(Verbosity.QUIET)
        elif shell_verbosity == 1:
            io.set_verbosity(Verbosity.VERBOSE)
        elif shell_verbosity == 2:
            io.set_verbosity(Verbosity.VERY_VERBOSE)
        elif shell_verbosity == 3:
            io.set_verbosity(Verbosity.DEBUG)
        else:
            shell_verbosity = 0

        if io.input.has_parameter_option(["--quiet", "-q"], True):
            io.set_verbosity(Verbosity.QUIET)
            shell_verbosity = -1
        else:
            if io.input.has_parameter_option("-vvv", True):
                io.set_verbosity(Verbosity.DEBUG)
                shell_verbosity = 3
            elif io.input.has_parameter_option("-vv", True):
                io.set_verbosity(Verbosity.VERY_VERBOSE)
                shell_verbosity = 2
            elif io.input.has_parameter_option(
                "-v", True
            ) or io.input.has_parameter_option("--verbose", only_params=True):
                io.set_verbosity(Verbosity.VERBOSE)
                shell_verbosity = 1

        if shell_verbosity == -1:
            io.interactive(False)

    @property
    def _default_definition(self) -> Definition:
        return Definition(
            [
                Argument(
                    "command",
                    required=True,
                    description="The command to execute.",
                ),
                Option(
                    "--help",
                    "-h",
                    flag=True,
                    description=(
                        "Display help for the given command. "
                        "When no command is given display help for "
                        f"the <info>{self._default_command}</info> command."
                    ),
                ),
                Option(
                    "--quiet", "-q", flag=True, description="Do not output any message."
                ),
                Option(
                    "--verbose",
                    "-v|vv|vvv",
                    flag=True,
                    description=(
                        "Increase the verbosity of messages: "
                        "1 for normal output, 2 for more verbose "
                        "output and 3 for debug."
                    ),
                ),
                Option(
                    "--version",
                    "-V",
                    flag=True,
                    description="Display this application version.",
                ),
                Option("--ansi", flag=True, description="Force ANSI output."),
                Option("--no-ansi", flag=True, description="Disable ANSI output."),
                Option(
                    "--no-interaction",
                    "-n",
                    flag=True,
                    description="Do not ask any interactive question.",
                ),
            ]
        )

    def _get_command_name(self, io: IO) -> str | None:
        if self._single_command:
            return self._default_command

        if "command" in io.input.arguments and io.input.argument("command"):
            candidates: list[str] = []
            for command_part in io.input.argument("command"):
                if candidates:
                    candidates.append(candidates[-1] + " " + command_part)
                else:
                    candidates.append(command_part)

            for candidate in reversed(candidates):
                if self.has(candidate):
                    return candidate

        return io.input.first_argument

    def extract_namespace(self, name: str, limit: int | None = None) -> str:
        parts = name.split(" ")[:-1]
        return " ".join(parts[:limit])

    def _get_default_ui(self) -> UI:
        from cleo.ui.progress_bar import ProgressBar

        io = self.create_io()
        return UI([ProgressBar(io)])

    def _extract_all_namespaces(self, name: str) -> list[str]:
        parts = name.split(" ")[:-1]
        namespaces: list[str] = []

        for part in parts:
            namespaces.append(namespaces[-1] + " " + part if namespaces else part)

        return namespaces

    def _init(self) -> None:
        if self._initialized:
            return

        self._initialized = True

        for command in self.default_commands:
            self.add(command)
