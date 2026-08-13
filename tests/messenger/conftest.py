import pytest

from expanse.messenger.serializers.serializer import Serializer
from expanse.serialization.serialization_manager import SerializationManager
from expanse.serialization.serializers.dataclass import DataclassSerializer


@pytest.fixture()
def serializer() -> Serializer:
    serialization_manager = SerializationManager()
    serialization_manager.register_serializer(DataclassSerializer())

    return Serializer(serialization_manager)
