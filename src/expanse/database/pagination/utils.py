import logging
import operator

from typing import Any
from typing import Literal

from sqlalchemy import Column
from sqlalchemy import ColumnElement
from sqlalchemy import Select
from sqlalchemy import and_
from sqlalchemy import or_
from sqlalchemy import tuple_
from sqlalchemy.sql.elements import Label
from sqlalchemy.sql.elements import _label_reference

from expanse.database.pagination.exceptions import DatabasePaginationError
from expanse.pagination.cursor.cursor import Cursor


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
            and order_by_clause.table is not None
            and order_by_clause.key
        ):
            # Default ASC order by
            column = getattr(order_by_clause.table.c, order_by_clause.key)
            order_by_columns.append((column, "asc"))
        elif isinstance(order_by_clause, _label_reference):
            # This happens when the query is ordered by an aliased column,
            # for instance: `query.order_by(Model.id.label("foo").desc())`
            element: ColumnElement[Any] | Label[Any] = order_by_clause.element
            if isinstance(element, Label):
                # Unspecified direction
                modifier = getattr(element.element, "modifier", None)
            else:
                modifier = getattr(element, "modifier", None)
                element = element.element

            direction: Literal["asc", "desc"] = (
                "desc" if modifier and modifier.__name__ == "desc_op" else "asc"
            )

            order_by_columns.append((element, direction))
        else:
            # This happens when the query is ordered by a direct column reference
            # with a modifier, for instance: `query.order_by(Model.id.desc())` or `query.order_by(column("id"))`

            # If it's a simple column there is no modifier so we assume ascending order
            if not hasattr(order_by_clause, "element"):
                direction = "asc"
                order_by_columns.append((order_by_clause, direction))
            else:
                direction = (
                    "desc" if order_by_clause.modifier.__name__ == "desc_op" else "asc"
                )
                order_by_columns.append((order_by_clause.element, direction))

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
            # All columns have the same direction, we can use tuple comparison
            op = conditions[0][0]
            columns_tuple = tuple(condition[1] for condition in conditions)
            values_tuple = tuple(condition[2] for condition in conditions)
            query = query.filter(op(tuple_(*columns_tuple), values_tuple))
        else:
            # Columns have different directions so we need to use a combination of OR conditions
            #
            # For instance, for an `ORDER BY a DESC, b ASC` with a cursor ({'a': a_val, 'b': b_val})
            # we would have `WHERE a < a_val OR (a = a_val AND b > b_val)`
            #
            # For 3+ columns: a < a_val OR (a = a_val AND (b < b_val OR (b = b_val AND c > c_val)))

            or_conditions = []
            for i, (op, column, value) in enumerate(conditions):
                if i == 0:
                    or_conditions.append(op(column, value))
                else:
                    equalities = [
                        conditions[j][1] == conditions[j][2] for j in range(i)
                    ]
                    condition = op(column, value)

                    or_conditions.append(and_(*equalities, condition))

            query = query.filter(or_(*or_conditions))

        # When the cursor is reversed, we need to reverse the order by clauses
        # to get the previous page instead of always getting the first page
        if cursor.is_reversed():
            reversed_order_by = [
                column.desc() if direction == "asc" else column.asc()
                for column, direction in order_by_columns
            ]

            query = query.order_by(None).order_by(*reversed_order_by)

    query = query.limit(size + 1)
    parameters = [column.name for column, _ in order_by_columns]

    return query, parameters, cursor
