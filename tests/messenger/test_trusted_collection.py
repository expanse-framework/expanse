from expanse.messenger.trusted_collection import TrustedCollection
from expanse.support._utils import class_to_name


class Foo:
    pass


def test_trust_classes() -> None:
    trusted_collection = TrustedCollection()

    trusted_collection.trust(Foo)

    assert trusted_collection.is_trusted(Foo)
    assert trusted_collection.is_trusted_name(class_to_name(Foo))


def test_distrust_classes() -> None:
    trusted_collection = TrustedCollection()

    trusted_collection.trust(Foo)
    trusted_collection.distrust(Foo)

    assert not trusted_collection.is_trusted(Foo)
    assert not trusted_collection.is_trusted_name(class_to_name(Foo))


def test_properties() -> None:
    trusted_collection = TrustedCollection()

    trusted_collection.trust(Foo)

    assert trusted_collection.classes == {
        Foo,
        *trusted_collection.get_default_classes(),
    }
    assert trusted_collection.class_names == {
        class_to_name(Foo),
        *(class_to_name(c) for c in trusted_collection.get_default_classes()),
    }


def test_get_default_classes() -> None:
    trusted_collection = TrustedCollection()

    assert len(trusted_collection.get_default_classes()) > 0
