import os
import sys

from contextlib import suppress

from cleo.application import Application as BaseApplication
from cleo.events.console_command_event import ConsoleCommandEvent
from cleo.events.console_error_event import ConsoleErrorEvent
from cleo.events.console_events import COMMAND
from cleo.events.console_events import ERROR
from cleo.events.console_events import TERMINATE
from cleo.events.console_terminate_event import ConsoleTerminateEvent
from cleo.exceptions import CleoError
from cleo.io.inputs.argument import Argument
from cleo.io.inputs.argv_input import ArgvInput
from cleo.io.inputs.definition import Definition
from cleo.io.inputs.input import Input
from cleo.io.io import IO
from cleo.io.outputs.output import Output

from expanse.asynchronous.console._adapters.command import Command


class Application(BaseApplication):
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

    async def _run(self, io: IO) -> int:
        if io.input.has_parameter_option(["--version", "-V"], True):
            io.write_line(self.long_version)

            return 0

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

            if io.input.script_name is not None:
                argv.insert(0, io.input.script_name)

            namespace = name.split(" ")[0]
            index = None
            for i, arg in enumerate(argv):
                if arg == namespace and i > 0:
                    argv[i] = name
                    index = i
                    break

            if index is not None:
                del argv[index + 1 : index + 1 + (len(name.split(" ")) - 1)]

            stream = io.input.stream
            interactive = io.input.is_interactive()
            io.set_input(ArgvInput(argv))
            io.input.set_stream(stream)
            io.input.interactive(interactive)

        exit_code = await self._run_command(command, io)
        self._running_command = None

        return exit_code

    async def _run_command(self, command: Command, io: IO) -> int:
        if self._event_dispatcher is None:
            return await command.run(io)

        # Bind before the console.command event,
        # so the listeners have access to the arguments and options
        try:
            command.merge_application_definition()
            io.input.bind(command.definition)
        except CleoError:
            # Ignore invalid option/arguments for now,
            # to allow the listeners to customize the definition
            pass

        command_event = ConsoleCommandEvent(command, io)
        error = None

        try:
            self._event_dispatcher.dispatch(command_event, COMMAND)

            if command_event.command_should_run():
                exit_code = await command.run(io)
            else:
                exit_code = ConsoleCommandEvent.RETURN_CODE_DISABLED
        except Exception as e:
            error_event = ConsoleErrorEvent(command, io, e)
            self._event_dispatcher.dispatch(error_event, ERROR)
            error = error_event.error
            exit_code = error_event.exit_code

            if exit_code == 0:
                error = None

        terminate_event = ConsoleTerminateEvent(command, io, exit_code)
        self._event_dispatcher.dispatch(terminate_event, TERMINATE)

        if error is not None:
            raise error

        return terminate_event.exit_code
