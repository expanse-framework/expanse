from typing import Any
from typing import Self
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
from sqlalchemy.sql.selectable import TypedReturnsRows


_T = TypeVar("_T", bound=Any)


class Connection(BaseConnection):
    @overload
    def scalar(
        self,
        statement: TypedReturnsRows[tuple[_T]],
        parameters: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> _T | None: ...

    @overload
    def scalar(
        self,
        statement: Executable,
        parameters: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> Any: ...

    @overload
    def scalar(
        self,
        statement: str,
        parameters: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> Any: ...

    def scalar(
        self,
        statement: TypedReturnsRows[tuple[_T]] | Executable | str,
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
        statement: TypedReturnsRows[tuple[_T]],
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> ScalarResult[_T]: ...

    @overload
    def scalars(
        self,
        statement: Executable,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> ScalarResult[Any]: ...

    @overload
    def scalars(
        self,
        statement: str,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> ScalarResult[Any]: ...

    def scalars(
        self,
        statement: TypedReturnsRows[tuple[_T]] | Executable | str,
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
        statement: TypedReturnsRows[_T],
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> CursorResult[_T]: ...

    @overload
    def execute(
        self,
        statement: Executable,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> CursorResult[Any]: ...

    @overload
    def execute(
        self,
        statement: str,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> CursorResult[Any]: ...

    def execute(
        self,
        statement: TypedReturnsRows[_T] | Executable | str,
        parameters: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: CoreExecuteOptionsParameter | None = None,
    ) -> CursorResult[Any]:
        if isinstance(statement, str):
            statement = text(statement)

        return super().execute(
            statement, parameters, execution_options=execution_options
        )

    def __enter__(self) -> Self:
        return self
