from pathlib import Path

from expanse.configuration.config import Config as ApplicationConfig
from expanse.contracts.routing.router import Router
from expanse.core.console.portal import Portal
from expanse.http.helpers import json
from expanse.http.helpers import view
from expanse.http.responses.response import Response
from expanse.openapi.config import OpenAPIConfig
from expanse.openapi.generator import OpenAPIGenerator
from expanse.support.service_provider import ServiceProvider
from expanse.view.view_finder import ViewFinder


class OpenAPIServiceProvider(ServiceProvider):
    async def register(self) -> None:
        await self._container.on_resolved(Portal, self.register_commands)
        await self._container.on_resolved(ViewFinder, self.add_views_path)
        await self._container.on_resolved(Router, self.register_routes)

        self._container.singleton(OpenAPIConfig, self.create_config)

    async def create_config(self, config: ApplicationConfig) -> "OpenAPIConfig":
        openapi_config = OpenAPIConfig(
            title="API",
            version=config["schematic"]["info"]["version"],
            description=config["schematic"]["info"]["description"],
        )

        return openapi_config

    async def register_commands(self, portal: Portal) -> None:
        portal = await self._container.get(Portal)
        await portal.load_path(Path(__file__).parent.joinpath("console/commands"))

    async def add_views_path(self, finder: ViewFinder) -> None:
        finder.add_paths([Path(__file__).parent.joinpath("views")])

    async def register_routes(self, router: Router) -> None:
        async def api_docs_ui(generator: OpenAPIGenerator) -> Response:
            return view("openapi/docs.jinja2", data={"spec": generator.generate()})

        async def api_docs(generator: OpenAPIGenerator) -> Response:
            return json(generator.generate())

        router.get("/docs/api", api_docs_ui)
        router.get("/docs/api.json", api_docs)
