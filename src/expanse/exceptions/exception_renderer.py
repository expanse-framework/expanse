import contextlib
import inspect
import os
import sys

from dataclasses import dataclass
from dataclasses import field
from http import HTTPStatus
from pathlib import Path

import expanse

from expanse.contracts.debug.exception_renderer import (
    ExceptionRenderer as ExceptionRendererContract,
)
from expanse.core.application import Application
from expanse.core.http.exceptions import HTTPException
from expanse.http.request import Request
from expanse.support.exceptions.frame import Frame
from expanse.support.exceptions.inspector import Inspector
from expanse.view.view_factory import ViewFactory
from expanse.view.view_finder import ViewFinder


@dataclass
class FrameModel:
    filepath: Path
    filename: str
    filepath_parts: list[str]
    function: str
    lineno: int
    code: str
    line: str
    highlighted_line: str


@dataclass
class FrameCollection:
    is_repeated: bool
    repetitions: int
    frames_count: int
    frames: list[FrameModel]
    is_vendor: bool = False


@dataclass
class Trace:
    error_name: str
    error_message: str
    frames: list[FrameCollection] = field(default_factory=list)


@dataclass
class Error:
    name: str
    message: str
    request: Request
    title: str = "Internal Server Error"
    traces: list[Trace] = field(default_factory=list)


class ExceptionRenderer(ExceptionRendererContract):
    def __init__(self, app: Application, view: ViewFactory, finder: ViewFinder) -> None:
        self._app: Application = app
        self._view: ViewFactory = view
        self._python_version: str = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        self._python_prefix: Path = Path(sys.prefix)

        finder.add_paths([Path(__file__).parent.joinpath("views")])

    async def render(self, exception: Exception, request: Request) -> str:
        return await self._view.render(
            self._view.make(
                "__expanse__/error",
                data={
                    "error": self.build_error(exception, request),
                    "python_version": self._python_version,
                    "expanse_version": expanse.__version__,
                    "asset_content": self.asset_content,
                },
            )
        )

    def build_error(self, exception: Exception, request: Request) -> Error:
        inspector: Inspector | None = Inspector(exception)
        title = HTTPStatus.INTERNAL_SERVER_ERROR.phrase
        if isinstance(exception, HTTPException):
            # Handle special 419 status code for CSRF token mismatch
            if exception.status_code == 419:
                title = "CSRF Token Mismatch"
            else:
                title = HTTPStatus(exception.status_code).phrase

        assert inspector is not None

        error = Error(
            name=inspector.exception_name,
            message=inspector.exception_message,
            request=request,
            title=title,
        )

        while inspector:
            trace = Trace(
                error_name=inspector.exception_name,
                error_message=inspector.exception_message,
            )
            for collection in inspector.frames.compact():
                frame_collection = FrameCollection(
                    is_repeated=collection.is_repeated(),
                    repetitions=collection.repetitions,
                    frames_count=0,
                    frames=[],
                )

                for i, frame in enumerate(reversed(collection)):
                    assert isinstance(frame, Frame)
                    filepath = Path(frame.filename)
                    is_vendor = filepath.is_relative_to(self._python_prefix)

                    with contextlib.suppress(ValueError):
                        filepath = filepath.relative_to(self._app.base_path)

                    if is_vendor != frame_collection.is_vendor:
                        if i == 0:
                            frame_collection.is_vendor = is_vendor
                        else:
                            trace.frames.append(frame_collection)
                            frame_collection = FrameCollection(
                                is_repeated=collection.is_repeated(),
                                repetitions=collection.repetitions,
                                frames_count=0,
                                frames=[],
                                is_vendor=is_vendor,
                            )

                    filename = filepath.name
                    frame_collection.frames_count += 1
                    frame_collection.frames.append(
                        FrameModel(
                            filepath=filepath,
                            filename=filename,
                            filepath_parts=str(filepath).split(os.path.sep),
                            function=frame.function,
                            lineno=frame.lineno,
                            code=self.highlight_frame(frame),
                            line=frame.line,
                            highlighted_line=self.highlight_frame(
                                frame, line_only=True
                            ),
                        )
                    )

                trace.frames.append(frame_collection)

            error.traces.append(trace)

            if inspector.previous_exception is not None:
                inspector = Inspector(inspector.previous_exception)
                continue

            inspector = None

        return error

    def highlight_frame(self, frame: Frame, line_only: bool = False) -> str:
        from pygments import highlight
        from pygments.formatters.html import HtmlFormatter
        from pygments.lexers import get_lexer_by_name

        lexer_name = "text"
        if frame.filename:
            filename = Path(frame.filename)

            if filename.suffix in {".jinja2", ".j2"}:
                lexer_name = "html+jinja"
            elif filename.suffix == ".py":
                lexer_name = "python"

        lexer = get_lexer_by_name(lexer_name)

        if line_only:
            return highlight(
                frame.line.strip(),
                lexer,
                HtmlFormatter(wrapcode=True),
            )

        if lexer_name == "html+jinja":
            source = [line + "\n" for line in Path(filename).read_text().splitlines()]
        else:
            module = inspect.getmodule(frame.frame)
            if module is None:
                return ""

            source = inspect.getsourcelines(module)[0]

        lines_before = 5
        lines_after = 5

        start_line = frame.lineno - lines_before

        start_line = max(start_line, 1)
        offset = start_line - 1
        length = lines_after + lines_before + 1

        snippet_lines = source[offset : offset + length]

        # The HTML will not properly display starting lines if they are simply new lines
        # So we discard them and adjust the starting line
        snippet_offset = 0
        for line in snippet_lines:
            if line.strip():
                break

            snippet_offset += 1
            start_line += 1

        code = "".join(snippet_lines[snippet_offset:])
        snippet_lineno = frame.lineno - start_line + 1

        return highlight(
            code,
            lexer,
            HtmlFormatter(
                linenos="inline",
                wrapcode=True,
                hl_lines=[snippet_lineno],
                linenostart=start_line,
            ),
        )

    def asset_content(self, asset_name: str) -> str:
        return Path(__file__).parent.joinpath("assets").joinpath(asset_name).read_text()
