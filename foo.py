from typing import ParamSpec
from typing import Protocol
from typing import TypeVar


T = TypeVar("T")
T_Cv = TypeVar("T_Cv", contravariant=True)
P = ParamSpec("P")


class _Adapter(Protocol[T_Cv, P]):
    async def __call__(
        self, raw_response: T_Cv, *args: P.args, **kwargs: P.kwargs
    ) -> int: ...


class Foo:
    def register(self, response: type[T], factory: _Adapter[T, P]) -> None: ...


class Bar: ...


async def bar(raw_response: Bar, baz: int, boom: str) -> int:
    return 42


foo = Foo()
foo.register(Bar, bar)
