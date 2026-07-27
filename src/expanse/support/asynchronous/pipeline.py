from collections.abc import Awaitable
from collections.abc import Callable
from functools import wraps
from typing import Self


type Pipe[I, O] = Callable[[I, Callable[[I], Awaitable[O]]], Awaitable[O]]


class Pipeline[I, O]:
    def __init__(self) -> None:
        self._pipes: list[Pipe[I, O]] = []
        self._input: I | None = None
        self._then: Callable[[O], Awaitable[None]] | None = None
        self._destination: Callable[[I], Awaitable[O]] | None = None

    def use(self, pipes: list[Pipe[I, O]]) -> Self:
        self._pipes = pipes

        return self

    def send(self, input: I) -> Self:
        self._input = input

        return self

    def to(self, destination: Callable[[I], Awaitable[O]]) -> Self:
        self._destination = destination

        return self

    def then(self, then: Callable[[O], Awaitable[None]]) -> Self:
        """
        Sets a callback to be executed after the pipeline has finished processing.

        This can be used for cleanup or logging purposes.

        :param then: An async callable that takes the output of the pipeline.
        """
        self._then = then

        return self

    async def run(self) -> O:
        if self._input is None:
            raise ValueError(
                "No input provided to the pipeline. Please call send() before to()."
            )

        if self._destination is None:
            raise ValueError(
                "No destination provided to the pipeline. Please call to() before run()."
            )

        pipeline = self._build(self._destination)

        result = await pipeline(self._input)

        if self._then is not None:
            await self._then(result)

        return result

    def _build(
        self, destination: Callable[[I], Awaitable[O]]
    ) -> Callable[[I], Awaitable[O]]:
        stack = destination

        for pipe in self._pipes[::-1]:
            stack = self._wrap(pipe)(stack)

        return stack

    def _wrap(
        self, pipe: Callable[[I, Callable[[I], Awaitable[O]]], Awaitable[O]]
    ) -> Callable[[Callable[[I], Awaitable[O]]], Callable[[I], Awaitable[O]]]:
        @wraps(pipe)
        def decorator(
            next_call: Callable[[I], Awaitable[O]],
        ) -> Callable[[I], Awaitable[O]]:
            @wraps(next_call)
            async def handler(i: I) -> O:
                return await pipe(i, next_call)

            return handler

        return decorator
