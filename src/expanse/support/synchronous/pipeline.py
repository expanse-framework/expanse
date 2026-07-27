from collections.abc import Callable
from functools import wraps
from typing import Self


class Pipeline[I, O]:
    def __init__(self) -> None:
        self._pipes: list[Callable[[I, Callable[[I], O]], O]] = []
        self._input: I | None = None
        self._destination: Callable[[I], O] | None = None
        self._then: Callable[[O], None] | None = None

    def use(self, pipes: list[Callable[[I, Callable[[I], O]], O]]) -> None:
        self._pipes = pipes

    def send(self, input: I) -> Self:
        self._input = input

        return self

    def to(self, destination: Callable[[I], O]) -> Self:
        self._destination = destination

        return self

    def then(self, then: Callable[[O], None]) -> Self:
        """
        Sets a callback to be executed after the pipeline has finished processing.

        This can be used for cleanup or logging purposes.

        :param then: A callable that takes the output of the pipeline.
        """
        self._then = then

        return self

    def run(self) -> O:
        if self._input is None:
            raise ValueError(
                "No input provided to the pipeline. Please call send() before to()."
            )

        if self._destination is None:
            raise ValueError(
                "No destination provided to the pipeline. Please call to() before run()."
            )

        pipeline = self._build(self._destination)

        result = pipeline(self._input)

        if self._then is not None:
            self._then(result)

        return result

    def _build(self, destination: Callable[[I], O]) -> Callable[[I], O]:
        stack = destination

        for pipe in self._pipes[::-1]:
            stack = self._wrap(pipe)(stack)

        return stack

    def _wrap(
        self, pipe: Callable[[I, Callable[[I], O]], O]
    ) -> Callable[[Callable[[I], O]], Callable[[I], O]]:
        @wraps(pipe)
        def decorator(
            next_call: Callable[[I], O],
        ) -> Callable[[I], O]:
            @wraps(next_call)
            def handler(i: I) -> O:
                return pipe(i, next_call)

            return handler

        return decorator
