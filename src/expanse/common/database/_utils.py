import inspect

from typing import Any
from typing import TypeVar
from typing import cast
from typing import overload

import sqlalchemy.engine.url as _url

from sqlalchemy import URL
from sqlalchemy import event
from sqlalchemy import exc
from sqlalchemy import util
from sqlalchemy.engine import Engine
from sqlalchemy.engine import base
from sqlalchemy.engine.create import _pool_translate_kwargs
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.engine.mock import create_mock_engine
from sqlalchemy.pool import ConnectionPoolEntry
from sqlalchemy.pool import _AdhocProxiedConnection
from sqlalchemy.sql import compiler


_T = TypeVar("_T", bound=Engine)


@overload
def create_engine(url: str | URL, engine_class: type[_T], **kwargs: Any) -> _T: ...


@overload
def create_engine(
    url: str | URL, engine_class: None = None, **kwargs: Any
) -> base.Engine: ...


def create_engine(
    url: str | URL, engine_class: type[_T] | None = None, **kwargs: Any
) -> _T | base.Engine:
    """
    This is a direct copy of the create_engine function from SQLAlchemy with added
    support for specifying the engine class. This is mainly useful to help with typing
    when having a custom connection class that extends the base Connection class.
    """

    if "strategy" in kwargs:
        strat = kwargs.pop("strategy")
        if strat == "mock":
            # this case is deprecated
            return create_mock_engine(url, **kwargs)  # type: ignore  # noqa: PGH003
        else:
            raise exc.ArgumentError(f"unknown strategy: {strat!r}")

    kwargs.pop("empty_in_strategy", None)

    # create url.URL object
    u = _url.make_url(url)

    u, plugins, kwargs = u._instantiate_plugins(kwargs)

    entrypoint = u._get_entrypoint()
    _is_async = kwargs.pop("_is_async", False)
    if _is_async:
        dialect_cls = entrypoint.get_async_dialect_cls(u)
    else:
        dialect_cls = entrypoint.get_dialect_cls(u)

    if kwargs.pop("_coerce_config", False):

        def pop_kwarg(key: str, default: Any | None = None) -> Any:
            value = kwargs.pop(key, default)
            if key in dialect_cls.engine_config_types:
                value = dialect_cls.engine_config_types[key](value)
            return value

    else:
        pop_kwarg = kwargs.pop  # type: ignore  # noqa: PGH003

    dialect_args = {}
    # consume dialect arguments from kwargs
    for k in util.get_cls_kwargs(dialect_cls):
        if k in kwargs:
            dialect_args[k] = pop_kwarg(k)

    dbapi = kwargs.pop("module", None)
    if dbapi is None:
        dbapi_args = {}

        if "import_dbapi" in dialect_cls.__dict__:
            dbapi_meth = dialect_cls.import_dbapi

        elif hasattr(dialect_cls, "dbapi") and inspect.ismethod(dialect_cls.dbapi):
            util.warn_deprecated(
                "The dbapi() classmethod on dialect classes has been "
                "renamed to import_dbapi().  Implement an import_dbapi() "
                f"classmethod directly on class {dialect_cls} to remove this "
                "warning; the old .dbapi() classmethod may be maintained for "
                "backwards compatibility.",
                "2.0",
            )
            dbapi_meth = dialect_cls.dbapi
        else:
            dbapi_meth = dialect_cls.import_dbapi

        for k in util.get_func_kwargs(dbapi_meth):
            if k in kwargs:
                dbapi_args[k] = pop_kwarg(k)
        dbapi = dbapi_meth(**dbapi_args)

    dialect_args["dbapi"] = dbapi

    dialect_args.setdefault("compiler_linting", compiler.NO_LINTING)
    enable_from_linting = kwargs.pop("enable_from_linting", True)
    if enable_from_linting:
        dialect_args["compiler_linting"] ^= compiler.COLLECT_CARTESIAN_PRODUCTS

    for plugin in plugins:
        plugin.handle_dialect_kwargs(dialect_cls, dialect_args)

    # create dialect
    dialect = dialect_cls(**dialect_args)

    # assemble connection arguments
    (cargs_tup, cparams) = dialect.create_connect_args(u)
    cparams.update(pop_kwarg("connect_args", {}))

    if "async_fallback" in cparams and util.asbool(cparams["async_fallback"]):
        util.warn_deprecated(
            "The async_fallback dialect argument is deprecated and will be "
            "removed in SQLAlchemy 2.1.",
            "2.0",
        )

    cargs = list(cargs_tup)  # allow mutability

    # look for existing pool or create
    pool = pop_kwarg("pool", None)
    if pool is None:

        def connect(
            connection_record: ConnectionPoolEntry | None = None,
        ) -> DBAPIConnection:
            if dialect._has_events:
                for fn in dialect.dispatch.do_connect:
                    connection = cast(
                        DBAPIConnection,
                        fn(dialect, connection_record, cargs, cparams),
                    )
                    if connection is not None:
                        return connection

            return dialect.connect(*cargs, **cparams)

        creator = pop_kwarg("creator", connect)

        poolclass = pop_kwarg("poolclass", None)
        if poolclass is None:
            poolclass = dialect.get_dialect_pool_class(u)
        pool_args = {"dialect": dialect}

        # consume pool arguments from kwargs, translating a few of
        # the arguments
        for k in util.get_cls_kwargs(poolclass):
            tk = _pool_translate_kwargs.get(k, k)
            if tk in kwargs:
                pool_args[k] = pop_kwarg(tk)

        for plugin in plugins:
            plugin.handle_pool_kwargs(poolclass, pool_args)

        pool = poolclass(creator, **pool_args)
    else:
        pool._dialect = dialect

    # create engine.
    if not pop_kwarg("future", True):
        raise exc.ArgumentError(
            "The 'future' parameter passed to "
            "create_engine() may only be set to True."
        )

    engineclass = engine_class or base.Engine

    engine_args = {}
    for k in util.get_cls_kwargs(engineclass):
        if k in kwargs:
            engine_args[k] = pop_kwarg(k)

    # internal flags used by the test suite for instrumenting / proxying
    # engines with mocks etc.
    _initialize = kwargs.pop("_initialize", True)

    # all kwargs should be consumed
    if kwargs:
        raise TypeError(
            "Invalid argument(s) {} sent to create_engine(), "
            "using configuration {}/{}/{}.  Please check that the "
            "keyword arguments are appropriate for this combination "
            "of components.".format(
                ",".join(f"'{k}'" for k in kwargs),
                dialect.__class__.__name__,
                pool.__class__.__name__,
                engineclass.__name__,
            )
        )

    engine = engineclass(pool, dialect, u, **engine_args)

    if _initialize:
        do_on_connect = dialect.on_connect_url(u)
        if do_on_connect:

            def on_connect(
                dbapi_connection: DBAPIConnection,
                connection_record: ConnectionPoolEntry,
            ) -> None:
                assert do_on_connect is not None
                do_on_connect(dbapi_connection)

            event.listen(pool, "connect", on_connect)

        builtin_on_connect = dialect._builtin_onconnect()
        if builtin_on_connect:
            event.listen(pool, "connect", builtin_on_connect)

        def first_connect(
            dbapi_connection: DBAPIConnection,
            connection_record: ConnectionPoolEntry,
        ) -> None:
            c = base.Connection(
                engine,
                connection=_AdhocProxiedConnection(dbapi_connection, connection_record),
                _has_events=False,
                # reconnecting will be a reentrant condition, so if the
                # connection goes away, Connection is then closed
                _allow_revalidate=False,
                # dont trigger the autobegin sequence
                # within the up front dialect checks
                _allow_autobegin=False,
            )
            c._execution_options = util.EMPTY_DICT

            try:
                dialect.initialize(c)
            finally:
                # note that "invalidated" and "closed" are mutually
                # exclusive in 1.4 Connection.
                if not c.invalidated and not c.closed:
                    # transaction is rolled back otherwise, tested by
                    # test/dialect/postgresql/test_dialect.py
                    # ::MiscBackendTest::test_initial_transaction_state
                    dialect.do_rollback(c.connection)

        # previously, the "first_connect" event was used here, which was then
        # scaled back if the "on_connect" handler were present.  now,
        # since "on_connect" is virtually always present, just use
        # "connect" event with once_unless_exception in all cases so that
        # the connection event flow is consistent in all cases.
        event.listen(pool, "connect", first_connect, _once_unless_exception=True)

    dialect_cls.engine_created(engine)
    if entrypoint is not dialect_cls:
        entrypoint.engine_created(engine)

    for plugin in plugins:
        plugin.engine_created(engine)

    return engine
