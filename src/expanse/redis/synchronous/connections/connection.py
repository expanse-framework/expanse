from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Any

from redis.commands.core import ACLCommands
from redis.commands.core import BasicKeyCommands
from redis.commands.core import FunctionCommands
from redis.commands.core import GeoCommands
from redis.commands.core import HashCommands
from redis.commands.core import HyperlogCommands
from redis.commands.core import ListCommands
from redis.commands.core import ManagementCommands
from redis.commands.core import ModuleCommands
from redis.commands.core import ScanCommands
from redis.commands.core import ScriptCommands
from redis.commands.core import SetCommands
from redis.commands.core import SortedSetCommands
from redis.commands.core import StreamCommands


if TYPE_CHECKING:
    from redis.connection import Encoder
    from redis.lock import Lock
    from redis.retry import Retry
    from redis.typing import KeyT


class Connection(
    ACLCommands,
    BasicKeyCommands,
    FunctionCommands,
    GeoCommands,
    HashCommands,
    HyperlogCommands,
    ListCommands,
    ManagementCommands,
    ModuleCommands,
    ScanCommands,
    ScriptCommands,
    SetCommands,
    SortedSetCommands,
    StreamCommands,
    ABC,
):
    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def get_encoder(self) -> Encoder: ...

    @abstractmethod
    def get_connection_kwargs(self) -> dict[str, Any | None]: ...

    @abstractmethod
    def set_retry(self, retry: Retry) -> None: ...

    @abstractmethod
    def pipeline(
        self,
        transaction: Any | None = None,
        shard_hint: Any | None = None,
    ) -> Any: ...

    @abstractmethod
    def transaction(self, func: Any, *watches: Any, **kwargs: Any) -> Any: ...

    @abstractmethod
    def lock(
        self,
        name: KeyT,
        timeout: float | None = None,
        sleep: float = 0.1,
        blocking: bool = True,
        blocking_timeout: float | None = None,
        lock_class: type[Lock] | None = None,
        thread_local: bool = True,
        raise_on_release_error: bool = True,
    ) -> Lock: ...

    @abstractmethod
    def parse_response(self, *args: Any, **kwargs: Any) -> Any: ...
