import inspect

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING
from typing import Annotated
from typing import TypeVar
from typing import get_args
from typing import get_origin
from typing import get_type_hints

import pytest

from expanse.container.container import Container
from expanse.core.helpers import _get_container
from expanse.core.helpers import _set_container


T = TypeVar("T")


if TYPE_CHECKING:
    type Inject[T] = T
else:

    class Inject:
        def __class_getitem__(cls, item: type[T]) -> T:
            return Annotated[type[T], cls.inject(item)]

        @classmethod
        def inject(cls, type: type[T]) -> T:
            async def _inject() -> T:
                container: Container | None = _get_container()

                if container is None:
                    raise RuntimeError("Container is not configured")

                return await container.get(type)

            return _inject


@pytest.fixture(scope="session")
async def container() -> AsyncGenerator[Container]:
    container = Container()

    _set_container(container)

    yield container

    await container.terminate()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Function, nextitem: pytest.Item | None):
    fixtures = item.fixturenames
    print(fixtures)
    print(item._fixtureinfo)
    defs = item._fixtureinfo.name2fixturedefs
    if diff := set(fixtures) ^ set(defs):
        print(diff)
        hints = get_type_hints(item.function, include_extras=True)
        print(inspect.signature(item.function))
        print(hints)
        for fixture in diff:
            annotation = hints.get(fixture)
            print(annotation)
            if not annotation:
                continue

            origin = get_origin(annotation)
            print(origin)
            if origin is not Annotated:
                continue

            args = get_args(annotation)
            print(args)
            if not args:
                continue

            call = args[1]
            if call.__name__ != "_inject":
                continue

            item._request._fixturemanager._arg2fixturedefs[fixture] = (
                pytest.FixtureDef(
                    item.config,
                    None,
                    argname=fixture,
                    func=call,
                    scope="function",
                    params=None,
                    _ispytest=True,
                ),
            )

    yield
