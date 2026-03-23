from collections.abc import Awaitable
from collections.abc import Callable
from functools import wraps
from typing import Self


type Pipe[I, O] = Callable[[I, Callable[[I], Awaitable[O]]], Awaitable[O]]


class Pipeline[I, O]:
    def __init__(self) -> None:
        self._pipes: list[Pipe[I, O]] = []
        self._input: I | None = None

    def use(self, pipes: list[Pipe[I, O]]) -> None:
        self._pipes = pipes

    def send(self, input: I) -> Self:
        self._input = input

        return self

    async def to(self, destination: Callable[[I], Awaitable[O]]) -> O:
        if self._input is None:
            raise ValueError(
                "No input provided to the pipeline. Please call send() before to()."
            )

        pipeline = self._build(destination)

        return await pipeline(self._input)

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
