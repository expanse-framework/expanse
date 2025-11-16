import logging
import operator

from typing import Any
from typing import Literal

from sqlalchemy import Column
from sqlalchemy import ColumnElement
from sqlalchemy import Select
from sqlalchemy import tuple_
from sqlalchemy.sql.elements import Label
from sqlalchemy.sql.elements import _label_reference

from expanse.database.pagination.exceptions import DatabasePaginationError
from expanse.pagination.cursor import Cursor


logger = logging.getLogger(__name__)


def prepare_pagination(
    query: Select[Any], size: int, cursor: Cursor | None = None
) -> tuple[Select[Any], list[str], Cursor | None]:
    order_by_columns: list[
        tuple[Column[Any] | Label[Any] | ColumnElement[Any], Literal["asc", "desc"]]
    ] = []
    for order_by_clause in query._order_by_clauses:
        if (
            hasattr(order_by_clause, "table")
            and hasattr(order_by_clause, "key")
            and order_by_clause.key
        ):
            # Default ASC order by
            column = getattr(order_by_clause.table.c, order_by_clause.key)
            order_by_columns.append((column, "asc"))

            continue
        elif isinstance(order_by_clause, _label_reference):
            # This happens when the query is ordered by an aliased column,
            # for instance: `query.order_by(Model.id.label("foo").desc())`
            element: ColumnElement[Any] | Label[Any] = order_by_clause.element
            if isinstance(order_by_clause.element, Label):
                modifier = getattr(order_by_clause.element.element, "modifier", None)
            else:
                modifier = getattr(element, "modifier", None)
                element = element.element

            direction = "desc" if modifier and modifier.__name__ == "desc_op" else "asc"

            order_by_columns.append((element, direction))
            continue
        else:
            direction = (
                "desc" if order_by_clause.modifier.__name__ == "desc_op" else "asc"
            )

            order_by_columns.append((order_by_clause.element, direction))
            continue

    if not order_by_columns:
        # Paginating requires order by clauses
        raise DatabasePaginationError(
            'Only queries with "order by" clauses can be properly paginated.'
        )

    if cursor:
        conditions = []
        directions: set[Literal["asc", "desc"]] = set()
        for column, direction in order_by_columns:
            parameter_value = cursor.parameter(column.name)
            if direction == "desc":
                op = operator.gt if cursor.is_reversed() else operator.lt
            else:
                op = operator.lt if cursor.is_reversed() else operator.gt

            conditions.append((op, column, parameter_value))
            directions.add(direction)

        if len(directions) == 1:
            op = conditions[0][0]
            columns_tuple = tuple(condition[1] for condition in conditions)
            values_tuple = tuple(condition[2] for condition in conditions)
            query = query.filter(op(tuple_(*columns_tuple), values_tuple))
        else:
            # TODO: Find a way to make it work for any direction. This should be possible
            # by building a combination of AND and OR conditions.
            raise DatabasePaginationError(
                "To deduplicate entries of the query all order by clauses must have the same direction"
            )

    query = query.limit(size + 1)
    parameters = [column.name for column, _ in order_by_columns]

    return query, parameters, cursor
