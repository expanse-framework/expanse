from pathlib import Path

import expanse.common.exceptions

from expanse.asynchronous.contracts.debug.exception_renderer import (
    ExceptionRenderer as ExceptionRendererContract,
)
from expanse.asynchronous.view.view_factory import ViewFactory
from expanse.asynchronous.view.view_finder import ViewFinder
from expanse.common.exceptions.exception_renderer import ExceptionRendererMixin


class ExceptionRenderer(ExceptionRendererContract, ExceptionRendererMixin):
    def __init__(self, view: ViewFactory, finder: ViewFinder) -> None:
        self._view = view

        finder.add_paths(
            [Path(expanse.common.exceptions.__file__).parent.joinpath("views")]
        )

    async def render(self, exception: Exception) -> str:
        trace = self.build_trace(exception)

        view = await self._view.make(
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
        return (
            Path(expanse.common.exceptions.__file__)
            .parent.joinpath("assets")
            .joinpath(asset_name)
            .read_text()
        )
