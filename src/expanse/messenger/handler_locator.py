from importlib import import_module
from pathlib import Path
from types import ModuleType

from expanse.core.application import Application
from expanse.messenger.registry import Registry
from expanse.messenger.utils import HandlerDefinition


class HandlerLocator:
    def __init__(self, app: Application, registry: Registry) -> None:
        self._app: Application = app
        self._registry: Registry = registry

    def register_handlers_from_directory(self, directory: Path) -> None:
        """
        Register handlers from the given directory.

        :param directory: The directory to search for handlers.
        """
        handlers = self.locate_handlers_in_directory(directory)
        for handler in handlers:
            self._registry.register(handler["message_type"], handler["handler"])

    def register_handlers_from_module(self, module: ModuleType) -> None:
        """
        Register handlers from the given module.

        :param module: The module to search for handlers.
        """
        handlers = self.locate_handlers_in_module(module)
        for handler in handlers:
            self._registry.register(handler["message_type"], handler["handler"])

    def locate_handlers_in_directory(self, directory: Path) -> list[HandlerDefinition]:
        """
        Locate handlers in the given directory.

        Only functions marked with the `message_handler` decorator.

        :param directory: The directory to search for handlers.
        :return: A list of callables that are handlers.
        """
        module_files = directory.glob("*.py")

        handlers = []

        for module_file in module_files:
            handlers.extend(self.locate_handlers_in_file(module_file))

        return handlers

    def locate_handlers_in_file(
        self,
        path: Path,
    ) -> list[HandlerDefinition]:
        """
        Locate handlers in the given file.

        Only functions marked with the `message_handler` decorator.

        :param path: The file to search for handlers.
        :return: A list of callables that are handlers.
        """
        path = relative_path = path.resolve()
        base_path = self._app.base_path

        relative_path = path.relative_to(base_path)

        module_name = (
            relative_path.with_suffix("")
            .as_posix()
            .replace("/", ".")
            .removesuffix(".__init__")
        )

        module = import_module(module_name)

        return self.locate_handlers_in_module(module)

    def locate_handlers_in_module(self, module: ModuleType) -> list[HandlerDefinition]:
        """
        Locate handlers in the given module.

        Only functions marked with the `message_handler` decorator.

        :param module: The module to search for handlers.
        :return: A list of callables that are handlers.
        """
        handlers = getattr(module, "__message_handlers__", {})

        return list(handlers.values())
