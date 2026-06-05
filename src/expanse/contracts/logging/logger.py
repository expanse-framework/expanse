from abc import ABC
from abc import abstractmethod
from typing import Any


class Logger(ABC):
    @abstractmethod
    def debug(self, message: str, *args: Any, **kwargs: Any) -> None: ...

    @abstractmethod
    def info(self, message: str, *args: Any, **kwargs: Any) -> None: ...

    @abstractmethod
    def warning(self, message: str, *args: Any, **kwargs: Any) -> None: ...

    @abstractmethod
    def error(self, message: str, *args: Any, **kwargs: Any) -> None: ...

    @abstractmethod
    def critical(self, message: str, *args: Any, **kwargs: Any) -> None: ...

    @abstractmethod
    def exception(
        self, message: str | BaseException, *args: Any, **kwargs: Any
    ) -> None: ...
