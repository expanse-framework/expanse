import inspect

from pathlib import Path
from typing import TypedDict

from crashtest.frame import Frame
from crashtest.inspector import Inspector

from expanse.contracts.debug.exception_renderer import (
    ExceptionRenderer as ExceptionRendererContract,
)
from expanse.view.view_factory import AsyncViewFactory
from expanse.view.view_finder import ViewFinder


class FrameDict(TypedDict):
    filepath: str
    filename: str
    function: str
    lineno: int
    code: str
    line: str
    highlighted_line: str
    number: int


class FrameCollection(TypedDict):
    is_repeated: bool
    repetitions: int
    frames_count: int
    frames: list[FrameDict]


class Trace(TypedDict):
    exception_name: str
    exception_message: str
    frames: list[FrameCollection]


class ExceptionRenderer(ExceptionRendererContract):
    def __init__(self, view: AsyncViewFactory, finder: ViewFinder) -> None:
        self._view = view

        finder.add_paths([Path(__file__).parent.joinpath("views")])

    async def render(self, exception: Exception) -> str:
        trace = self.build_trace(exception)

        view = self._view.make(
            "__expanse__/trace",
            {
                "error": {
                    "type": trace["exception_name"],
                    "message": trace["exception_message"],
                },
                "trace": trace["frames"],
                "asset_content": self.asset_content,
            },
        )

        return await self._view.render(view, raw=True)

    def asset_content(self, asset_name: str) -> str:
        return Path(__file__).parent.joinpath("assets").joinpath(asset_name).read_text()

    def build_trace(self, error: Exception) -> Trace:
        inspector = Inspector(error)
        trace = Trace(
            exception_name=inspector.exception_name,
            exception_message=inspector.exception_message,
            frames=[],
        )
        frames: list[FrameCollection] = []
        frames_count = len(inspector.frames)

        i = frames_count
        for collection in reversed(inspector.frames.compact()):
            frame_collection: FrameCollection = {
                "is_repeated": collection.is_repeated(),
                "repetitions": collection.repetitions,
                "frames_count": len(collection),
                "frames": [],
            }
            if collection.is_repeated():
                i -= len(collection) * (collection.repetitions + 1)

            for frame in reversed(collection):
                assert isinstance(frame, Frame)
                filepath = frame.filename
                filename = Path(filepath).name
                frame_collection["frames"].append(
                    {
                        "filepath": filepath,
                        "filename": filename,
                        "function": frame.function,
                        "lineno": frame.lineno,
                        "code": self.highlight_frame(frame),
                        "line": frame.line,
                        "highlighted_line": self.highlight_frame(frame, line_only=True),
                        "number": i,
                    }
                )
                i -= 1

            frames.append(frame_collection)

        trace["frames"] = frames

        return trace

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
                source = [frame.line or ""]
            else:
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
