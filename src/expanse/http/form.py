import dataclasses

from collections.abc import MutableMapping
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar
from typing import cast

import msgspec

from pydantic import BaseModel
from pydantic import ValidationError

from expanse.http._datastructures import FormData
from expanse.support._model_types import is_msgspec_struct
from expanse.support._model_types import is_pydantic_model
from expanse.support._model_types import parse_msgspec_validation_error


if TYPE_CHECKING:
    from pydantic_core import ErrorDetails

    from expanse.support._datastructures import MultiMapping


Model = TypeVar("Model", bound=type[BaseModel] | type[msgspec.Struct])


@dataclasses.dataclass
class Field:
    name: str
    value: Any
    error: str | None = None

    def is_valid(self) -> bool:
        return self.error is not None


class Form[T: BaseModel | msgspec.Struct]:
    data: T | None
    _model: type[T] | None = None

    def __init__(self, data: MutableMapping[str, Any] | FormData | None = None) -> None:
        self._submitted = data
        self.fields: dict[str, Field] = {}
        self.errors: list[ErrorDetails] = []
        self.data: T | None = None
        form_data: MutableMapping[str, Any] | MultiMapping[str, Any] = {}
        if self._submitted is not None:
            form_data = self._submitted

        if self._model and is_pydantic_model(self._model):
            for field_name, _field_info in self._model.model_fields.items():
                self.fields[field_name] = Field(
                    name=field_name, value=form_data.get(field_name)
                )

            if self._submitted is not None:
                try:
                    self.data = cast("T", self._model.model_validate(form_data))
                except ValidationError as e:
                    self.errors = e.errors()

                    for error in self.errors:
                        field = self.fields.get(cast("str", error["loc"][0]))
                        if not field:
                            continue

                        field.error = error["msg"]
        elif self._model and is_msgspec_struct(self._model):
            for field_info in msgspec.structs.fields(self._model):
                self.fields[field_info.name] = Field(
                    name=field_info.name, value=form_data.get(field_info.name)
                )

            if self._submitted is not None:
                try:
                    self.data = cast(
                        "T",
                        msgspec.convert(form_data, type=self._model, strict=False),
                    )
                except msgspec.ValidationError as e:
                    message, loc = parse_msgspec_validation_error(e)
                    error_detail: ErrorDetails = {
                        "type": "validation_error",
                        "loc": tuple(loc),
                        "msg": message,
                        "input": None,
                    }
                    self.errors = [error_detail]

                    error_field_name = cast("str | None", loc[0] if loc else None)
                    field = (
                        self.fields.get(error_field_name) if error_field_name else None
                    )
                    if field:
                        field.error = message
        else:
            for name, value in form_data.items():
                self.fields[name] = Field(name=name, value=value)

    def is_valid(self) -> bool:
        return not bool(self.errors)

    def is_submitted(self) -> bool:
        return self._submitted is not None

    def __class_getitem__(cls, item: type[T]) -> type["Form[T]"]:
        klass = type(cls.__name__, (cls,), {"_model": item})

        assert issubclass(klass, Form)

        return klass
