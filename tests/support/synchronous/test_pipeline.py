from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from expanse.support.synchronous.pipeline import Pipeline


if TYPE_CHECKING:
    from collections.abc import Callable


def _destination(value: int) -> int:
    return value + 1


def test_run_returns_destination_result_without_pipes() -> None:
    result = Pipeline[int, int]().send(1).to(_destination).run()

    assert result == 2


def test_run_executes_pipes_in_order_before_destination() -> None:
    calls: list[str] = []

    def first(value: int, next_call: Callable[[int], int]) -> int:
        calls.append("first-in")
        result = next_call(value + 1)
        calls.append("first-out")
        return result

    def second(value: int, next_call: Callable[[int], int]) -> int:
        calls.append("second-in")
        result = next_call(value * 10)
        calls.append("second-out")
        return result

    pipeline: Pipeline[int, int] = Pipeline()
    pipeline.use([first, second])

    result = pipeline.send(1).to(_destination).run()

    assert result == 21
    assert calls == ["first-in", "second-in", "second-out", "first-out"]


def test_then_is_called_with_pipeline_output() -> None:
    seen: list[int] = []

    def then(value: int) -> None:
        seen.append(value)

    result = Pipeline[int, int]().send(5).to(_destination).then(then).run()

    assert result == 6
    assert seen == [6]


def test_then_runs_after_destination() -> None:
    order: list[str] = []

    def destination(value: int) -> int:
        order.append("destination")
        return value

    def then(value: int) -> None:
        order.append("then")

    Pipeline[int, int]().send(1).to(destination).then(then).run()

    assert order == ["destination", "then"]


def test_then_is_optional() -> None:
    result = Pipeline[int, int]().send(1).to(_destination).run()

    assert result == 2


def test_run_raises_when_send_was_not_called() -> None:
    with pytest.raises(ValueError, match=r"No input provided to the pipeline"):
        Pipeline[int, int]().to(_destination).run()


def test_run_raises_when_to_was_not_called() -> None:
    with pytest.raises(ValueError, match=r"No destination provided to the pipeline"):
        Pipeline[int, int]().send(1).run()


def test_send_to_and_then_return_the_pipeline() -> None:
    pipeline: Pipeline[int, int] = Pipeline()

    def then(value: int) -> None: ...

    assert pipeline.send(1) is pipeline
    assert pipeline.to(_destination) is pipeline
    assert pipeline.then(then) is pipeline
