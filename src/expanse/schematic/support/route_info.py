from typing import TYPE_CHECKING

from expanse.routing.route import Route
from expanse.schematic.analyzers.signature_analyzer import SignatureAnalyzer
from expanse.schematic.analyzers.signature_analyzer import SignatureInfo
from expanse.schematic.inference.inference import Inference
from expanse.schematic.support.doc_string.doc_string import DocString


if TYPE_CHECKING:
    from expanse.schematic.support.doc_string.doc_string_info import DocStringInfo


class RouteInfo:
    def __init__(self, route: Route, inference: Inference) -> None:
        self.signature: SignatureInfo = SignatureAnalyzer().analyze(route)
        self.route: Route = route
        self.func = (
            route.endpoint
            if not isinstance(route.endpoint, tuple)
            else getattr(route.endpoint[0], route.endpoint[1])
        )
        self._inference: Inference = inference
        self.doc_string: DocStringInfo = DocString.parse(self.func.__doc__ or "")
