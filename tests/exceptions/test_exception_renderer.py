from pathlib import Path

from pytest_mock import MockerFixture

from expanse.core.application import Application
from expanse.exceptions.exception_renderer import ExceptionRenderer
from expanse.http.request import Request
from expanse.view.view_factory import ViewFactory
from expanse.view.view_finder import ViewFinder
from tests.exceptions.fixtures.exceptions import foo


async def test_the_correct_stack_trace_representation_is_passed_to_view(
    app: Application, mocker: MockerFixture
) -> None:
    view = await app.container.get(ViewFactory)

    renderer = ExceptionRenderer(app, view, await app.container.get(ViewFinder))
    request = Request.create("http://example.com", "GET")
    make = mocker.spy(view, "make")

    try:
        await foo()
    except Exception as e:
        await renderer.render(e, request)

    call_args = make.call_args_list[0]
    view_name = call_args[0][0]
    data = call_args[1]["data"]
    assert view_name == "__expanse__/error"
    assert data["error"].name == "Exception"
    assert data["error"].message == "Custom exception"
    assert data["error"].request == request
    assert data["error"].title == "Internal Server Error"

    traces = data["error"].traces
    assert len(traces) == 1

    trace = traces[0].frames
    assert not trace[0].is_repeated
    assert trace[0].repetitions == -1
    assert trace[0].frames_count == 3

    frames = trace[0].frames
    assert frames[0].filepath == (
        Path(__file__)
        .parent.joinpath("fixtures/exceptions.py")
        .relative_to(app.base_path)
    )
    assert frames[0].filename == "exceptions.py"
    assert frames[0].function == "bar"
    assert frames[0].lineno == 11

    assert frames[1].filepath == (
        Path(__file__)
        .parent.joinpath("fixtures/exceptions.py")
        .relative_to(app.base_path)
    )
    assert frames[1].filename == "exceptions.py"
    assert frames[1].function == "foo"
    assert frames[1].lineno == 7

    assert frames[2].filepath == Path(__file__).relative_to(app.base_path)
    assert frames[2].filename == "test_exception_renderer.py"
    assert (
        frames[2].function
        == "test_the_correct_stack_trace_representation_is_passed_to_view"
    )
    assert frames[2].lineno == 23
