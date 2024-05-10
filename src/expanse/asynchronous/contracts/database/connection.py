from typing import Any
from typing import TypeVar
from typing import overload

from sqlalchemy import CursorResult
from sqlalchemy import Executable
from sqlalchemy import ScalarResult
from sqlalchemy import text
from sqlalchemy.engine.interfaces import CoreExecuteOptionsParameter
from sqlalchemy.engine.interfaces import _CoreAnyExecuteParams
from sqlalchemy.engine.interfaces import _CoreSingleExecuteParams
from sqlalchemy.ext.asyncio import AsyncConnection as BaseAsyncConnection


_T = TypeVar("_T", bound=Any)


class Connection(BaseAsyncConnection):
    @overload
    async def scalar(
        self,
        statement: Executable | str,
        parameters: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> Any: ...

    async def scalar(
        self,
        statement: Executable,
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
        statement: Executable | str,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> ScalarResult[Any]: ...

    async def scalars(
        self,
        statement: Executable | str,
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
        statement: Executable | str,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> CursorResult[Any]: ...

    async def execute(
        self,
        statement: Executable | str,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> CursorResult[Any]:
        if isinstance(statement, str):
            statement = text(statement)

        return await super().execute(
            statement, parameters, execution_options=execution_options
        )
