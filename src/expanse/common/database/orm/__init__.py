from collections.abc import Callable
from typing import Any
from typing import Literal
from typing import TypeVar

from sqlalchemy.orm import MappedColumn
from sqlalchemy.orm import mapped_column
from sqlalchemy.sql._typing import _AutoIncrementType
from sqlalchemy.sql._typing import _InfoType
from sqlalchemy.sql._typing import _TypeEngineArgument
from sqlalchemy.sql.base import SchemaEventTarget
from sqlalchemy.sql.base import _NoArg
from sqlalchemy.sql.schema import FetchedValue
from sqlalchemy.sql.schema import SchemaConst
from sqlalchemy.sql.schema import _ServerDefaultArgument


_T = TypeVar("_T")


def column(
    __name_pos: str | _TypeEngineArgument | SchemaEventTarget | None = None,
    __type_pos: _TypeEngineArgument | SchemaEventTarget | None = None,
    *args: SchemaEventTarget,
    init: bool = False,
    repr: _NoArg | bool = _NoArg.NO_ARG,
    default: Any | None = _NoArg.NO_ARG,
    default_factory: _NoArg | Callable[[], _T] = _NoArg.NO_ARG,
    compare: _NoArg | bool = _NoArg.NO_ARG,
    kw_only: _NoArg | bool = _NoArg.NO_ARG,
    nullable: bool
    | Literal[SchemaConst.NULL_UNSPECIFIED]
    | None = SchemaConst.NULL_UNSPECIFIED,
    primary_key: bool | None = False,
    deferred: _NoArg | bool = _NoArg.NO_ARG,
    deferred_group: str | None = None,
    deferred_raiseload: bool | None = None,
    use_existing_column: bool = False,
    name: str | None = None,
    type_: _TypeEngineArgument | None = None,
    autoincrement: _AutoIncrementType = "auto",
    doc: str | None = None,
    key: str | None = None,
    index: bool | None = None,
    unique: bool | None = None,
    info: _InfoType | None = None,
    onupdate: Any | None = None,
    insert_default: Any | None = _NoArg.NO_ARG,
    server_default: _ServerDefaultArgument | None = None,
    server_onupdate: FetchedValue | None = None,
    active_history: bool = False,
    quote: bool | None = None,
    system: bool = False,
    comment: str | None = None,
    sort_order: _NoArg | int = _NoArg.NO_ARG,
    **kw: Any,
) -> MappedColumn:
    return mapped_column(
        __name_pos,
        __type_pos,
        *args,
        init=init,
        repr=repr,
        default=default,
        default_factory=default_factory,
        compare=compare,
        kw_only=kw_only,
        nullable=nullable,
        primary_key=primary_key,
        deferred=deferred,
        deferred_group=deferred_group,
        deferred_raiseload=deferred_raiseload,
        use_existing_column=use_existing_column,
        name=name,
        type_=type_,
        autoincrement=autoincrement,
        doc=doc,
        key=key,
        index=index,
        unique=unique,
        info=info,
        onupdate=onupdate,
        insert_default=insert_default,
        server_default=server_default,
        server_onupdate=server_onupdate,
        active_history=active_history,
        quote=quote,
        system=system,
        comment=comment,
        sort_order=sort_order,
        **kw,
    )
