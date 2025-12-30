from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Self
from typing import TypeVar
from typing import cast
from typing import overload

from sqlalchemy import CursorResult
from sqlalchemy import Executable
from sqlalchemy import Result
from sqlalchemy import ScalarResult
from sqlalchemy import Select
from sqlalchemy import Table
from sqlalchemy import UpdateBase
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy import util
from sqlalchemy.orm import Session as BaseSession
from sqlalchemy.sql import func


if TYPE_CHECKING:
    from types import EllipsisType

    from sqlalchemy.engine.interfaces import _CoreAnyExecuteParams
    from sqlalchemy.engine.interfaces import _CoreSingleExecuteParams
    from sqlalchemy.orm._typing import OrmExecuteOptionsParameter
    from sqlalchemy.orm.session import _BindArguments
    from sqlalchemy.sql.selectable import TypedReturnsRows

    from expanse.database.synchronous.cursor_paginator import CursorPaginator
    from expanse.pagination.cursor.cursor import Cursor
    from expanse.pagination.offset.paginator import Paginator
    from expanse.pagination.pagination_manager import PaginationManager


_T = TypeVar("_T", bound=Any)


class Session(BaseSession):
    _pagination_manager: PaginationManager | None = None

    @overload  # type: ignore[override]
    def execute(
        self,
        statement: UpdateBase,
        params: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: _BindArguments | None = None,
        _parent_execute_state: Any | None = None,
        _add_event: Any | None = None,
    ) -> CursorResult[Any]: ...

    @overload
    def execute(
        self,
        statement: Executable,
        params: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: _BindArguments | None = None,
        _parent_execute_state: Any | None = None,
        _add_event: Any | None = None,
    ) -> Result[Any]: ...

    @overload
    def execute(
        self,
        statement: str,
        params: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
        _parent_execute_state: Any | None = None,
        _add_event: Any | None = None,
    ) -> Result[Any]: ...

    def execute(
        self,
        statement: UpdateBase | Executable | str,
        params: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: _BindArguments | None = None,
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
        statement: TypedReturnsRows[tuple[_T]],
        params: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: _BindArguments | None = None,
        **kw: Any,
    ) -> _T | None: ...

    @overload
    def scalar(
        self,
        statement: Executable,
        params: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: _BindArguments | None = None,
        **kw: Any,
    ) -> Any: ...

    @overload
    def scalar(
        self,
        statement: str,
        params: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: _BindArguments | None = None,
        **kw: Any,
    ) -> Any: ...

    def scalar(
        self,
        statement: TypedReturnsRows[tuple[_T]] | Executable | str,
        params: _CoreSingleExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: _BindArguments | None = None,
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
        statement: TypedReturnsRows[tuple[_T]],
        params: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: _BindArguments | None = None,
        **kw: Any,
    ) -> ScalarResult[_T]: ...

    @overload
    def scalars(
        self,
        statement: Executable,
        params: _CoreAnyExecuteParams | None = None,
        *,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: _BindArguments | None = None,
        **kw: Any,
    ) -> ScalarResult[Any]: ...

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

    @overload
    def paginate(
        self,
        statement: TypedReturnsRows[tuple[_T]],
        params: _CoreAnyExecuteParams | None = None,
        *,
        per_page: int,
        page: int | EllipsisType = ...,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: _BindArguments | None = None,
        **kw: Any,
    ) -> Paginator[_T]: ...

    @overload
    def paginate(
        self,
        statement: Executable,
        params: _CoreAnyExecuteParams | None = None,
        *,
        per_page: int,
        page: int | EllipsisType = ...,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: _BindArguments | None = None,
        **kw: Any,
    ) -> Paginator[Any]: ...

    def paginate(
        self,
        statement: TypedReturnsRows[tuple[_T]] | Executable,
        params: _CoreAnyExecuteParams | None = None,
        *,
        per_page: int,
        page: int | EllipsisType = ...,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
        **kw: Any,
    ) -> Paginator[Any]:
        from expanse.pagination.offset.paginator import Paginator

        if page is ...:
            # No current page was explicitly provided,
            # use the session's pagination manager if available.
            page = (
                self._pagination_manager.resolve_page()
                if self._pagination_manager is not None
                else 1
            )

        # Cast to Select for type safety - paginate only works with Select statements
        select_statement = cast("Select[Any]", statement)

        total = self.execute(
            select(func.count()).select_from(
                select_statement.order_by(None).limit(None).offset(None).subquery()
            )
        ).scalar_one()

        select_statement = select_statement.limit(per_page + 1).offset(
            (page - 1) * per_page
        )

        # Determine if we need to return scalars or raw rows.
        # by checking if all the columns are tables, i.e. complete models in an ORM context.
        # Only in that case do we return scalars.
        raw_results = not all(
            isinstance(column, Table) for column in select_statement._raw_columns
        )
        if raw_results:
            results = self.execute(
                select_statement,
                params,
                execution_options=execution_options,
                bind_arguments=bind_arguments,
                **kw,
            ).all()
        else:
            results = self.scalars(
                select_statement,
                params,
                execution_options=execution_options,
                bind_arguments=bind_arguments,
                **kw,
            ).all()

        return Paginator(
            items=results,
            per_page=per_page,
            current_page=page,
            total=total,
        )

    @overload
    def cursor_paginate(
        self,
        statement: TypedReturnsRows[tuple[_T]],
        params: _CoreAnyExecuteParams | None = None,
        *,
        per_page: int,
        cursor: Cursor | None | EllipsisType = ...,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: _BindArguments | None = None,
        **kw: Any,
    ) -> CursorPaginator[_T]: ...

    @overload
    def cursor_paginate(
        self,
        statement: Executable,
        params: _CoreAnyExecuteParams | None = None,
        *,
        per_page: int,
        cursor: Cursor | None | EllipsisType = ...,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: _BindArguments | None = None,
        **kw: Any,
    ) -> CursorPaginator[Any]: ...

    def cursor_paginate(
        self,
        statement: TypedReturnsRows[tuple[_T]] | Executable,
        params: _CoreAnyExecuteParams | None = None,
        *,
        per_page: int,
        cursor: Cursor | None | EllipsisType = ...,
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
        **kw: Any,
    ) -> CursorPaginator[Any]:
        from expanse.database.pagination.utils import prepare_pagination
        from expanse.database.synchronous.cursor_paginator import CursorPaginator

        if isinstance(statement, str):
            statement = text(statement)

        if cursor is ...:
            # No cursor was explicitly provided, use the session's pagination manager if available.
            cursor = (
                self._pagination_manager.resolve_cursor()
                if self._pagination_manager is not None
                else None
            )

        # Cast to Select for type safety - prepare_pagination expects Select
        select_statement = cast("Select[Any]", statement)
        select_statement, parameters, cursor = prepare_pagination(
            select_statement, per_page, cursor=cursor
        )

        # Determine if we need to return scalars or raw rows.
        # by checking if all the columns are tables, i.e. complete models in an ORM context.
        # Only in that case do we return scalars.
        raw_results = not all(
            isinstance(column, Table) for column in select_statement._raw_columns
        )
        if raw_results:
            results = self.execute(
                select_statement,
                params,
                execution_options=execution_options,
                bind_arguments=bind_arguments,
                **kw,
            ).all()
        else:
            results = self.scalars(
                select_statement,
                params,
                execution_options=execution_options,
                bind_arguments=bind_arguments,
                **kw,
            ).all()

        return CursorPaginator(
            items=results,
            query=select_statement,
            session=self,
            per_page=per_page,
            cursor=cursor,
            parameters=parameters,
        )

    def set_pagination_manager(self, manager: PaginationManager) -> Self:
        self._pagination_manager = manager

        return self
