from collections.abc import Generator
from typing import Any
from typing import Self
from typing import TypeVar
from typing import cast
from typing import overload

from sqlalchemy import CursorResult
from sqlalchemy import Executable
from sqlalchemy import ScalarResult
from sqlalchemy import text
from sqlalchemy.engine.interfaces import CoreExecuteOptionsParameter
from sqlalchemy.engine.interfaces import _CoreAnyExecuteParams
from sqlalchemy.engine.interfaces import _CoreSingleExecuteParams
from sqlalchemy.ext.asyncio import AsyncConnection as BaseAsyncConnection
from sqlalchemy.sql.selectable import TypedReturnsRows


_T = TypeVar("_T", bound=Any)


class Connection(BaseAsyncConnection):
    @overload
    async def scalar(
        self,
        statement: TypedReturnsRows[tuple[_T]],
        parameters: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> _T | None: ...

    @overload
    async def scalar(
        self,
        statement: Executable,
        parameters: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> Any: ...

    @overload
    async def scalar(
        self,
        statement: str,
        parameters: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> Any: ...

    async def scalar(
        self,
        statement: TypedReturnsRows[tuple[_T]] | Executable | str,
        parameters: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> Any:
        if isinstance(statement, str):
            statement = text(statement)

        return await super().scalar(
            statement, parameters, execution_options=execution_options
        )

    @overload
    async def scalars(
        self,
        statement: TypedReturnsRows[tuple[_T]],
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> ScalarResult[_T]: ...

    @overload
    async def scalars(
        self,
        statement: Executable,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> ScalarResult[Any]: ...

    @overload
    async def scalars(
        self,
        statement: str,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> ScalarResult[Any]: ...

    async def scalars(
        self,
        statement: TypedReturnsRows[tuple[_T]] | Executable | str,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> ScalarResult[Any]:
        if isinstance(statement, str):
            statement = text(statement)

        return await super().scalars(
            statement, parameters, execution_options=execution_options
        )

    @overload
    async def execute(
        self,
        statement: TypedReturnsRows[_T],
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> CursorResult[_T]: ...

    @overload
    async def execute(
        self,
        statement: Executable,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> CursorResult[Any]: ...

    @overload
    async def execute(
        self,
        statement: str,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> CursorResult[Any]: ...

    async def execute(
        self,
        statement: TypedReturnsRows[_T] | Executable | str,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> CursorResult[Any]:
        if isinstance(statement, str):
            statement = text(statement)

        return await super().execute(
            statement, parameters, execution_options=execution_options
        )

    def __aenter__(self) -> Self:  # type: ignore[override]
        return self

    def __await__(self) -> Generator[Any, None, Self]:
        return cast(Generator[Any, None, Self], super().__await__())
