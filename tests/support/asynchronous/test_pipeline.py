from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from expanse.support.asynchronous.pipeline import Pipeline


if TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable


async def _destination(value: int) -> int:
    return value + 1


async def test_run_returns_destination_result_without_pipes() -> None:
    result = await Pipeline[int, int]().send(1).to(_destination).run()

    assert result == 2


async def test_run_executes_pipes_in_order_before_destination() -> None:
    calls: list[str] = []

    async def first(value: int, next_call: Callable[[int], Awaitable[int]]) -> int:
        calls.append("first-in")
        result = await next_call(value + 1)
        calls.append("first-out")
        return result

    async def second(value: int, next_call: Callable[[int], Awaitable[int]]) -> int:
        calls.append("second-in")
        result = await next_call(value * 10)
        calls.append("second-out")
        return result

    result = await (
        Pipeline[int, int]().use([first, second]).send(1).to(_destination).run()
    )

    assert result == 21
    assert calls == ["first-in", "second-in", "second-out", "first-out"]


async def test_then_is_called_with_pipeline_output() -> None:
    seen: list[int] = []

    async def then(value: int) -> None:
        seen.append(value)

    result = await Pipeline[int, int]().send(5).to(_destination).then(then).run()

    assert result == 6
    assert seen == [6]


async def test_then_runs_after_destination_and_pipes() -> None:
    order: list[str] = []

    async def pipe(value: int, next_call: Callable[[int], Awaitable[int]]) -> int:
        order.append("pipe")
        return await next_call(value)

    async def destination(value: int) -> int:
        order.append("destination")
        return value

    async def then(value: int) -> None:
        order.append("then")

    await Pipeline[int, int]().use([pipe]).send(1).to(destination).then(then).run()

    assert order == ["pipe", "destination", "then"]


async def test_then_is_optional() -> None:
    result = await Pipeline[int, int]().send(1).to(_destination).run()

    assert result == 2


async def test_run_raises_when_send_was_not_called() -> None:
    with pytest.raises(ValueError, match=r"No input provided to the pipeline"):
        await Pipeline[int, int]().to(_destination).run()


async def test_run_raises_when_to_was_not_called() -> None:
    with pytest.raises(ValueError, match=r"No destination provided to the pipeline"):
        await Pipeline[int, int]().send(1).run()


async def test_send_use_to_and_then_return_the_pipeline() -> None:
    pipeline: Pipeline[int, int] = Pipeline()

    async def then(value: int) -> None: ...

    assert pipeline.send(1) is pipeline
    assert pipeline.use([]) is pipeline
    assert pipeline.to(_destination) is pipeline
    assert pipeline.then(then) is pipeline
