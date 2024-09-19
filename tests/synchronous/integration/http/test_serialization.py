from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel
from pydantic import ConfigDict

from expanse.routing.router import Router
from expanse.testing.client import TestClient


@dataclass
class Foo:
    bar: str
    baz: int = 42


class User:
    def __init__(self, first_name: str, last_name: str, email: str) -> None:
        self.first_name = first_name
        self.last_name = last_name
        self.email = email


class UserData(BaseModel):
    first_name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


def serialize_dataclass() -> Foo:
    return Foo("bar")


def serialize_with_pydantic_model() -> Annotated[User, UserData]:
    return User("John", "Doe", "john@doe.com")


def serialize_list_with_pydantic_model() -> list[Annotated[User, UserData]]:
    return [User("John", "Doe", "john@doe.com"), User("Jane", "Doe", "jane@doe.com")]


def test_dataclasses_are_automatically_serialized(
    client: TestClient, router: Router
) -> None:
    router.get("/", serialize_dataclass)

    response = client.get("/")

    assert response.json() == {"bar": "bar", "baz": 42}


def test_objects_can_be_serialized_with_pydantic_models(
    client: TestClient, router: Router
) -> None:
    router.get("/", serialize_with_pydantic_model)

    response = client.get("/")

    assert response.json() == {"first_name": "John", "email": "john@doe.com"}


def test_list_of_objects_can_be_serialized_with_pydantic_models(
    client: TestClient, router: Router
) -> None:
    router.get("/", serialize_list_with_pydantic_model)

    response = client.get("/")

    assert response.json() == [
        {"first_name": "John", "email": "john@doe.com"},
        {"first_name": "Jane", "email": "jane@doe.com"},
    ]
