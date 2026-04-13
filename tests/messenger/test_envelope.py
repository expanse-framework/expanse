from dataclasses import dataclass

import msgspec

from expanse.messenger.envelope import Envelope


@dataclass
class MyMessage:
    content: str


class StampA(msgspec.Struct):
    value: str


class StampB(msgspec.Struct):
    value: int


def test_wrap_creates_envelope_from_message() -> None:
    message = MyMessage(content="hello")
    envelope = Envelope.wrap(message)

    assert envelope.open() is message


def test_wrap_returns_existing_envelope() -> None:
    message = MyMessage(content="hello")
    envelope = Envelope(message)
    wrapped = Envelope.wrap(envelope)

    assert wrapped is envelope


def test_wrap_with_stamps() -> None:
    message = MyMessage(content="hello")
    stamp = StampA(value="test")
    envelope = Envelope.wrap(message, stamps=[stamp])

    assert envelope.stamp(StampA) is stamp


def test_open_returns_message() -> None:
    message = MyMessage(content="hello")
    envelope = Envelope(message)

    assert envelope.open() is message


def test_with_stamps_returns_new_envelope() -> None:
    message = MyMessage(content="hello")
    envelope = Envelope(message)
    new_envelope = envelope.with_stamps(StampA(value="a"))

    assert new_envelope is not envelope
    assert new_envelope.has_stamp(StampA)
    assert not envelope.has_stamp(StampA)


def test_with_stamps_preserves_existing_stamps() -> None:
    stamp_a = StampA(value="a")
    stamp_b = StampB(value=1)
    envelope = Envelope(MyMessage(content="hello"), stamps=[stamp_a])
    new_envelope = envelope.with_stamps(stamp_b)

    assert new_envelope.stamp(StampA) is stamp_a
    assert new_envelope.stamp(StampB) is stamp_b


def test_stamp_returns_last_stamp_of_type() -> None:
    stamp1 = StampA(value="first")
    stamp2 = StampA(value="second")
    envelope = Envelope(MyMessage(content="hello"), stamps=[stamp1, stamp2])

    assert envelope.stamp(StampA) is stamp2


def test_stamp_returns_none_when_not_found() -> None:
    envelope = Envelope(MyMessage(content="hello"))

    assert envelope.stamp(StampA) is None


def test_has_stamp() -> None:
    envelope = Envelope(MyMessage(content="hello"), stamps=[StampA(value="a")])

    assert envelope.has_stamp(StampA) is True
    assert envelope.has_stamp(StampB) is False


def test_is_stamped() -> None:
    envelope = Envelope(MyMessage(content="hello"))
    assert envelope.is_stamped() is False

    stamped = envelope.with_stamps(StampA(value="a"))
    assert stamped.is_stamped() is True


def test_stamps_with_type_returns_all_of_type() -> None:
    stamp1 = StampA(value="first")
    stamp2 = StampA(value="second")
    envelope = Envelope(
        MyMessage(content="hello"), stamps=[stamp1, stamp2, StampB(value=1)]
    )

    result = envelope.stamps(StampA)
    assert result == [stamp1, stamp2]


def test_stamps_with_type_returns_empty_list_when_not_found() -> None:
    envelope = Envelope(MyMessage(content="hello"))

    assert envelope.stamps(StampA) == []


def test_without_stamps_removes_given_types() -> None:
    envelope = Envelope(
        MyMessage(content="hello"),
        stamps=[StampA(value="a"), StampB(value=1)],
    )
    new_envelope = envelope.without_stamps(StampA)

    assert not new_envelope.has_stamp(StampA)
    assert new_envelope.has_stamp(StampB)


def test_without_stamps_removes_multiple_types() -> None:
    envelope = Envelope(
        MyMessage(content="hello"),
        stamps=[StampA(value="a"), StampB(value=1)],
    )
    new_envelope = envelope.without_stamps(StampA, StampB)

    assert not new_envelope.has_stamp(StampA)
    assert not new_envelope.has_stamp(StampB)
    assert not new_envelope.is_stamped()


def test_stamps_returns_flat_list() -> None:
    stamp_a = StampA(value="a")
    stamp_b = StampB(value=1)
    envelope = Envelope(MyMessage(content="hello"), stamps=[stamp_a, stamp_b])

    stamps = envelope.stamps()
    assert stamp_a in stamps
    assert stamp_b in stamps
    assert len(stamps) == 2
