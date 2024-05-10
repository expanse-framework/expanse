from typing import Any
from typing import overload

from sqlalchemy import Executable
from sqlalchemy import Result
from sqlalchemy import ScalarResult
from sqlalchemy import text
from sqlalchemy import util
from sqlalchemy.engine.interfaces import _CoreAnyExecuteParams
from sqlalchemy.engine.interfaces import _CoreSingleExecuteParams
from sqlalchemy.orm import Session as BaseSession
from sqlalchemy.orm._typing import OrmExecuteOptionsParameter


class Session(BaseSession):
    @overload
    def execute(
        self,
        statement: str,
        params: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter | None = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
        _parent_execute_state: Any | None = None,
        _add_event: Any | None = None,
    ) -> Result[Any]: ...

    def execute(
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

        return super().execute(
            statement,
            params,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
            _parent_execute_state=_parent_execute_state,
            _add_event=_add_event,
        )

    @overload
    def scalar(
        self,
        statement: str,
        params: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
        **kw: Any,
    ) -> Any: ...

    def scalar(
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

        return super().scalar(
            statement,
            params,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
            **kw,
        )

    @overload
    def scalars(
        self,
        statement: str,
        params: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
        **kw: Any,
    ) -> ScalarResult[Any]: ...

    def scalars(
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

        return super().scalars(
            statement,
            params,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
            **kw,
        )
