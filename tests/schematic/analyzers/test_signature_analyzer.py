from typing import Annotated

from pydantic import BaseModel

from expanse.http.json import JSON
from expanse.http.query import Query
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.routing.route import Route
from expanse.schematic.analyzers.signature_analyzer import SignatureAnalyzer


class UserModel(BaseModel):
    """A user model."""

    name: str
    email: str
    age: int | None = None


def test_signature_analyzer_detects_path_parameters():
    """Test that path parameters are correctly identified."""

    def handler(user_id: int) -> dict:
        return {"id": user_id}

    route = Route.get("/users/{user_id}", handler)
    analyzer = SignatureAnalyzer()

    info = analyzer.analyze(route)

    assert len(info.path_parameters) == 1
    assert info.path_parameters[0].name == "user_id"
    assert info.path_parameters[0].kind == "path"
    assert info.path_parameters[0].is_required is True


def test_signature_analyzer_detects_query_parameters():
    """Test that query parameters are correctly identified."""

    def handler(name: str, age: int = 0) -> dict:
        return {"name": name, "age": age}

    route = Route.get("/users", handler)
    analyzer = SignatureAnalyzer()

    info = analyzer.analyze(route)

    assert len(info.query_parameters) == 2
    assert info.query_parameters[0].name == "name"
    assert info.query_parameters[0].kind == "query"
    assert info.query_parameters[0].is_required is True

    assert info.query_parameters[1].name == "age"
    assert info.query_parameters[1].kind == "query"
    assert info.query_parameters[1].is_required is False


def test_signature_analyzer_detects_json_body_with_pydantic():
    """Test that JSON body with Pydantic model is correctly identified."""

    def handler(user: Annotated[UserModel, JSON]) -> dict:
        return {"user": user.name}

    route = Route.post("/users", handler)
    analyzer = SignatureAnalyzer()

    info = analyzer.analyze(route)

    assert info.body_parameter is not None
    assert info.body_parameter.name == "user"
    assert info.body_parameter.kind == "body"
    assert info.body_parameter.pydantic_model == UserModel
    assert info.body_parameter.data_source == JSON


def test_signature_analyzer_detects_query_with_pydantic():
    """Test that query parameters with Pydantic model are correctly identified."""

    def handler(filters: Annotated[UserModel, Query]) -> dict:
        return {"filters": filters.name}

    route = Route.get("/users", handler)
    analyzer = SignatureAnalyzer()

    info = analyzer.analyze(route)

    assert len(info.query_parameters) == 1
    assert info.query_parameters[0].name == "filters"
    assert info.query_parameters[0].kind == "query"
    assert info.query_parameters[0].pydantic_model == UserModel


def test_signature_analyzer_detects_dependencies():
    """Test that dependency injections are correctly identified."""

    def handler(request: Request, response: Response) -> dict:
        return {}

    route = Route.get("/users", handler)
    analyzer = SignatureAnalyzer()

    info = analyzer.analyze(route)

    assert info.has_request is True
    assert info.has_response is True
    assert len(info.query_parameters) == 0


def test_signature_analyzer_extracts_return_annotation():
    """Test that return type annotation is extracted."""

    def handler() -> dict[str, str]:
        return {}

    route = Route.get("/users", handler)
    analyzer = SignatureAnalyzer()

    info = analyzer.analyze(route)

    assert info.return_annotation == dict[str, str]


def test_signature_analyzer_handles_mixed_parameters():
    """Test complex signature with mixed parameter types."""

    def handler(
        user_id: int,
        request: Request,
        name: str = "default",
        user: Annotated[UserModel, JSON] | None = None,
    ) -> dict:
        return {}

    route = Route.post("/users/{user_id}", handler)
    analyzer = SignatureAnalyzer()

    info = analyzer.analyze(route)

    assert len(info.path_parameters) == 1
    assert info.path_parameters[0].name == "user_id"

    assert info.has_request is True

    assert len(info.query_parameters) == 1
    assert info.query_parameters[0].name == "name"

    assert info.body_parameter is not None
    assert info.body_parameter.name == "user"
