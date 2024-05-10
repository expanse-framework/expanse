from typing import Any
from typing import overload

from sqlalchemy import Executable
from sqlalchemy import Result
from sqlalchemy import ScalarResult
from sqlalchemy import text
from sqlalchemy import util
from sqlalchemy.engine.interfaces import _CoreAnyExecuteParams
from sqlalchemy.engine.interfaces import _CoreSingleExecuteParams
from sqlalchemy.ext.asyncio import AsyncSession as BaseAsyncSession
from sqlalchemy.orm._typing import OrmExecuteOptionsParameter


class Session(BaseAsyncSession):
    @overload
    async def execute(
        self,
        statement: str,
        params: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter | None = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
        _parent_execute_state: Any | None = None,
        _add_event: Any | None = None,
    ) -> Result[Any]: ...

    async def execute(
        self,
        statement: Executable | str,
        params: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
        _parent_execute_state: Any | None = None,
        _add_event: Any | None = None,
    ) -> Result[Any]:
        if isinstance(statement, str):
            statement = text(statement)

        return await super().execute(
            statement,
            params,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
            _parent_execute_state=_parent_execute_state,
            _add_event=_add_event,
        )

    @overload
    async def scalar(
        self,
        statement: str,
        params: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
        **kw: Any,
    ) -> Any: ...

    async def scalar(
        self,
        statement: Executable | str,
        params: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
        **kw: Any,
    ) -> Any:
        if isinstance(statement, str):
            statement = text(statement)

        return await super().scalar(
            statement,
            params,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
            **kw,
        )

    @overload
    async def scalars(
        self,
        statement: str,
        params: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
        **kw: Any,
    ) -> ScalarResult[Any]: ...

    async def scalars(
        self,
        statement: Executable | str,
        params: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
        **kw: Any,
    ) -> ScalarResult[Any]:
        if isinstance(statement, str):
            statement = text(statement)

        return await super().scalars(
            statement,
            params,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
            **kw,
        )
