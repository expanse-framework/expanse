from collections.abc import AsyncGenerator
from collections.abc import AsyncIterable
from collections.abc import AsyncIterator
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from functools import partial
from typing import TypeVar

from anyio import CancelScope
from anyio import create_task_group

from expanse.http.responses.response import Response
from expanse.support._concurrency import AsyncIteratorWrapper
from expanse.types import Receive
from expanse.types import Send


T = TypeVar("T")

type StreamType[T] = Iterable[T] | Iterator[T] | AsyncIterable[T] | AsyncIterator[T]


class StreamedResponse(Response):
    __slots__ = ("iterator",)

    def __init__(
        self,
        iterator: StreamType[bytes | str] | Callable[[], StreamType[bytes | str]],
        *,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        content_type: str | None = None,
        encoding: str = "utf-8",
    ) -> None:
        super().__init__(
            content=None,
            status_code=status_code,
            headers=headers,
            content_type=content_type,
            encoding=encoding,
        )

        self.iterator: (
            StreamType[bytes | str] | Callable[[], StreamType[bytes | str]]
        ) = iterator

    async def _stream(self, send: Send) -> None:
        """
        Send the response as a stream of chunks via ASGI events
        """
        iterator: AsyncIterable[str | bytes] | AsyncGenerator[str | bytes, None]
        it = self.iterator

        if callable(it):
            # If the iterator is a callable, we call it to get the actual iterator
            it = it()

        if not isinstance(it, AsyncIterable | AsyncIterator):
            iterator = AsyncIteratorWrapper[bytes | str](it)
        else:
            iterator = it

        async for chunk in iterator:
            await send(
                {
                    "type": "http.response.body",
                    "body": chunk.encode(self.encoding)
                    if isinstance(chunk, str)
                    else chunk,
                    "more_body": True,
                }
            )

        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def _listen_for_disconnect(
        self, cancel_scope: CancelScope, receive: Receive
    ) -> None:
        if not cancel_scope.cancel_called:
            message = await receive()
            if message["type"] == "http.disconnect":
                cancel_scope.cancel()
            else:
                await self._listen_for_disconnect(
                    cancel_scope=cancel_scope, receive=receive
                )

    async def send_body(self, send: Send, receive: Receive) -> None:
        async with create_task_group() as task_group:
            task_group.start_soon(partial(self._stream, send))
            await self._listen_for_disconnect(
                cancel_scope=task_group.cancel_scope, receive=receive
            )
