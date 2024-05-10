from typing import Any
from typing import TypeVar
from typing import overload

from sqlalchemy import Connection as BaseConnection
from sqlalchemy import CursorResult
from sqlalchemy import Executable
from sqlalchemy import ScalarResult
from sqlalchemy import text
from sqlalchemy.engine.interfaces import CoreExecuteOptionsParameter
from sqlalchemy.engine.interfaces import _CoreAnyExecuteParams
from sqlalchemy.engine.interfaces import _CoreSingleExecuteParams


_T = TypeVar("_T", bound=Any)


class Connection(BaseConnection):
    @overload
    def scalar(
        self,
        statement: Executable | str,
        parameters: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> Any: ...

    def scalar(
        self,
        statement: Executable | str,
        parameters: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> Any:
        if isinstance(statement, str):
            statement = text(statement)

        return super().scalar(
            statement, parameters, execution_options=execution_options
        )

    @overload
    def scalars(
        self,
        statement: Executable | str,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> ScalarResult[Any]: ...

    def scalars(
        self,
        statement: Executable | str,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> ScalarResult[Any]:
        if isinstance(statement, str):
            statement = text(statement)

        return super().scalars(
            statement, parameters, execution_options=execution_options
        )

    @overload
    def execute(
        self,
        statement: Executable | str,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> CursorResult[Any]: ...

    def execute(
        self,
        statement: Executable | str,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> CursorResult[Any]:
        if isinstance(statement, str):
            statement = text(statement)

        return super().execute(
            statement, parameters, execution_options=execution_options
        )
