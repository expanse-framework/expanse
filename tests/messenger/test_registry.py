from dataclasses import dataclass

import pytest

from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import UntrustedMessageTypeError
from expanse.messenger.registry import Registry
from expanse.messenger.serializers.serializer import Serializer
from expanse.messenger.trusted_collection import TrustedCollection
from expanse.serialization.serialization_manager import SerializationManager
from expanse.serialization.serializers.dataclass import DataclassSerializer


@dataclass
class Foo:
    value: str


async def handler(message: Foo) -> None:
    pass


def test_register_trusts_the_message_type_when_a_trusted_collection_is_provided() -> (
    None
):
    trusted_collection = TrustedCollection()
    registry = Registry(trusted_collection)

    registry.register(Foo, handler)

    assert trusted_collection.is_trusted(Foo)


def test_register_handler_trusts_the_inferred_message_type() -> None:
    trusted_collection = TrustedCollection()
    registry = Registry(trusted_collection)

    registry.register_handler(handler)

    assert trusted_collection.is_trusted(Foo)


def test_register_without_a_trusted_collection_does_not_raise() -> None:
    registry = Registry()

    registry.register(Foo, handler)

    assert registry.get_handlers(Foo) == [handler]


def _make_serializer(trusted_collection: TrustedCollection) -> Serializer:
    serialization_manager = SerializationManager()
    serialization_manager.register_serializer(
        DataclassSerializer().restrict(trusted_collection.class_names)
    )

    return Serializer(serialization_manager)


def test_a_registered_message_type_can_be_decoded_under_strict_mode() -> None:
    """
    Regression test: registering a handler must be enough to make its message
    type decodable once serializers are restricted to the trusted collection,
    as happens when `messenger.strict` is enabled.
    """
    trusted_collection = TrustedCollection()
    registry = Registry(trusted_collection)
    registry.register(Foo, handler)

    serializer = _make_serializer(trusted_collection)

    encoded = serializer.encode(Envelope.wrap(Foo(value="bar")))
    decoded = serializer.decode(encoded)

    assert decoded.open() == Foo(value="bar")


def test_decoding_a_type_that_was_never_registered_is_rejected() -> None:
    trusted_collection = TrustedCollection()
    registry = Registry(trusted_collection)
    registry.register(Foo, handler)

    encoded = _make_serializer(trusted_collection).encode(
        Envelope.wrap(Foo(value="bar"))
    )

    # A different process/collection that never registered a handler for `Foo`.
    stranger_serializer = _make_serializer(TrustedCollection())

    with pytest.raises(UntrustedMessageTypeError):
        stranger_serializer.decode(encoded)
