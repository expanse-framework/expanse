from pathlib import Path

from expanse.configuration.config import Config
from expanse.contracts.routing.router import Router
from expanse.core.console.portal import Portal
from expanse.http.helpers import json
from expanse.http.helpers import view
from expanse.http.response import Response
from expanse.schematic.generator import Generator
from expanse.schematic.generator_config import GeneratorConfig
from expanse.schematic.inference.inference import Inference
from expanse.schematic.support.operation_builder import OperationBuilder
from expanse.support.service_provider import ServiceProvider
from expanse.view.view_finder import ViewFinder


class SchematicServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.schematic.generator_config import GeneratorConfig

        await self._container.on_resolved(Portal, self.register_commands)
        await self._container.on_resolved(ViewFinder, self.add_views_path)
        await self._container.on_resolved(Router, self.register_routes)

        self._container.singleton(GeneratorConfig, self.create_config)
        self._container.singleton(OperationBuilder, self.create_operation_builder)
        self._container.singleton(Inference, self.create_inference)

    async def create_config(self, config: Config) -> "GeneratorConfig":
        from expanse.schematic.generator_config import GeneratorConfig

        generator_config = GeneratorConfig(config["schematic"])

        return generator_config

    async def create_operation_builder(self) -> OperationBuilder:
        from expanse.schematic.support.extensions.operations.error_response import (
            ErrorResponseExtension,
        )
        from expanse.schematic.support.extensions.operations.essentials import (
            EssentialsExtension,
        )
        from expanse.schematic.support.extensions.operations.pagination_response import (
            PaginationResponseExtension,
        )
        from expanse.schematic.support.extensions.operations.parameters import (
            ParametersExtension,
        )
        from expanse.schematic.support.extensions.operations.request_body import (
            RequestBodyExtension,
        )
        from expanse.schematic.support.extensions.operations.response import (
            ResponseExtension,
        )

        operation_builder = OperationBuilder()
        operation_builder.set_extensions(
            [
                EssentialsExtension,
                ParametersExtension,
                RequestBodyExtension,
                ResponseExtension,
                ErrorResponseExtension,
                PaginationResponseExtension,
            ]
        )

        return operation_builder

    async def create_inference(self) -> Inference:
        from expanse.schematic.inference.extensions.abort_detector import AbortDetector
        from expanse.schematic.inference.extensions.http_exception_detector import (
            HTTPExceptionDetector,
        )
        from expanse.schematic.inference.extensions.response_detector import (
            ResponseDetector,
        )

        inference = Inference()
        inference.add_extension(AbortDetector())
        inference.add_extension(HTTPExceptionDetector())
        inference.add_extension(ResponseDetector())

        return inference

    async def register_commands(self, portal: Portal) -> None:
        portal = await self._container.get(Portal)
        await portal.load_path(Path(__file__).parent.joinpath("console/commands"))

    async def register_routes(self, router: Router) -> None:
        async def api_docs_ui(
            generator: Generator, config: GeneratorConfig, router: Router
        ) -> Response:
            return view(
                "openapi/docs.jinja2",
                data={"spec": generator.generate(config, router).to_dict()},
            )

        async def api_docs(
            generator: Generator, config: GeneratorConfig, router: Router
        ) -> Response:
            return json(generator.generate(config, router).to_dict())

        router.get("/docs/api", api_docs_ui)
        router.get("/docs/api.json", api_docs)

    async def add_views_path(self, finder: ViewFinder) -> None:
        finder.add_paths([Path(__file__).parent.joinpath("views")])
