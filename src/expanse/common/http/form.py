import dataclasses

from collections.abc import MutableMapping
from typing import Any
from typing import Generic
from typing import NotRequired
from typing import TypeVar
from typing import cast

from baize.datastructures import FormData
from baize.datastructures import MultiMapping
from pydantic import BaseModel
from pydantic import ValidationError
from typing_extensions import TypedDict


Model = TypeVar("Model", bound=type[BaseModel])


class ErrorDetails(TypedDict):
    type: str
    loc: tuple[int | str, ...]
    msg: str
    input: Any
    ctx: NotRequired[dict[str, Any]]


@dataclasses.dataclass
class Field:
    name: str
    value: Any
    error: str | None = None

    def is_valid(self) -> bool:
        return self.error is not None


T = TypeVar("T", bound=BaseModel)


class Form(Generic[T]):
    data: T | None
    _model: type[T] | None = None

    def __init__(self, data: MutableMapping[str, Any] | FormData | None = None) -> None:
        self._submitted = data
        self.fields: dict[str, Field] = {}
        self.errors: list[ErrorDetails] = []
        self.data: T | None = None
        form_data: MutableMapping[str, Any] | MultiMapping = {}
        if self._submitted is not None:
            form_data = self._submitted

        if self._model:
            for field_name, _field_info in self._model.model_fields.items():
                self.fields[field_name] = Field(
                    name=field_name, value=form_data.get(field_name)
                )

            if self._submitted is not None:
                try:
                    self.data = self._model.model_validate(form_data)
                except ValidationError as e:
                    self.errors = e.errors()

                    for error in self.errors:
                        field = self.fields.get(cast(str, error["loc"][0]))
                        if not field:
                            continue

                        field.error = error["msg"]
        else:
            for name, value in form_data.items():
                self.fields[name] = Field(name=name, value=value)

    def is_valid(self) -> bool:
        return not bool(self.errors)

    def __class_getitem__(cls, item: type[T]) -> type["Form"]:
        klass = type(cls.__name__, (cls,), {"_model": item})

        assert issubclass(klass, Form)

        return klass
