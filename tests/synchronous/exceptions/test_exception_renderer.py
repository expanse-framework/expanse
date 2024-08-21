from pathlib import Path

from pytest_mock import MockerFixture

from expanse.core.application import Application
from expanse.exceptions.exception_renderer import ExceptionRenderer
from expanse.view.view_factory import ViewFactory
from expanse.view.view_finder import ViewFinder
from tests.synchronous.exceptions.fixtures.exceptions import foo


def test_the_correct_stack_trace_representation_is_passed_to_view(
    app: Application, mocker: MockerFixture
) -> None:
    view = app.container.make(ViewFactory)

    renderer = ExceptionRenderer(view, app.container.make(ViewFinder))

    make = mocker.spy(view, "make")

    try:
        foo()
    except Exception as e:
        renderer.render(e)

    call_args = make.call_args_list[0][0]
    assert call_args[0] == "__expanse__/trace"
    assert call_args[1]["error"] == {"type": "Exception", "message": "Custom exception"}

    trace = call_args[1]["trace"]
    assert not trace[0]["is_repeated"]
    assert trace[0]["repetitions"] == -1
    assert trace[0]["frames_count"] == 2

    frames = trace[0]["frames"]
    assert frames[0]["filepath"] == str(
        Path(__file__).parent.joinpath("fixtures/exceptions.py")
    )
    assert frames[0]["filename"] == "exceptions.py"
    assert frames[0]["function"] == "foo"
    assert frames[0]["lineno"] == 7
    assert frames[0]["number"] == 3

    assert frames[1]["filepath"] == str(Path(__file__))
    assert frames[1]["filename"] == "test_exception_renderer.py"
    assert (
        frames[1]["function"]
        == "test_the_correct_stack_trace_representation_is_passed_to_view"
    )
    assert frames[1]["lineno"] == 22
    assert frames[1]["number"] == 2
