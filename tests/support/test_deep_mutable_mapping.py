import pytest

from expanse.support.deep_mutable_mapping import DeepMutableMapping


def test_init_stores_top_level_keys() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1, b=2)

    assert mapping["a"] == 1
    assert mapping["b"] == 2


def test_init_without_arguments_yields_empty_mapping() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping()

    assert len(mapping) == 0
    assert list(mapping) == []


def test_getitem_returns_top_level_value() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1)

    assert mapping["a"] == 1


def test_getitem_returns_nested_value_via_dotted_key() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a={"b": {"c": 42}})

    assert mapping["a.b.c"] == 42


def test_getitem_raises_key_error_for_missing_top_level_key() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping()

    with pytest.raises(KeyError):
        mapping["missing"]


def test_getitem_raises_key_error_for_missing_nested_key() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a={"b": 1})

    with pytest.raises(KeyError):
        mapping["a.missing"]


def test_setitem_sets_top_level_value() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping()

    mapping["a"] = 1

    assert mapping["a"] == 1


def test_setitem_creates_intermediate_dicts_for_dotted_key() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping()

    mapping["a.b.c"] = 42

    assert mapping["a"] == {"b": {"c": 42}}
    assert mapping["a.b"] == {"c": 42}
    assert mapping["a.b.c"] == 42


def test_setitem_preserves_existing_sibling_keys() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a={"x": 1})

    mapping["a.y"] = 2

    assert mapping["a"] == {"x": 1, "y": 2}


def test_setitem_overwrites_existing_value() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1)

    mapping["a"] = 2

    assert mapping["a"] == 2


def test_delitem_removes_top_level_key() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1, b=2)

    del mapping["a"]

    assert "a" not in mapping
    assert mapping["b"] == 2


def test_delitem_removes_nested_key() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a={"b": {"c": 1, "d": 2}})

    del mapping["a.b.c"]

    assert "a.b.c" not in mapping
    assert mapping["a.b.d"] == 2


def test_delitem_raises_key_error_for_missing_top_level_key() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping()

    with pytest.raises(KeyError):
        del mapping["missing"]


def test_delitem_raises_key_error_for_missing_nested_key() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a={"b": 1})

    with pytest.raises(KeyError):
        del mapping["a.missing"]


def test_iter_yields_only_top_level_keys() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a={"b": 1}, c=2)

    assert set(iter(mapping)) == {"a", "c"}


def test_len_counts_only_top_level_keys() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a={"b": 1, "c": 2}, d=3)

    assert len(mapping) == 2


def test_contains_returns_true_for_top_level_key() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1)

    assert "a" in mapping


def test_contains_returns_true_for_nested_dotted_key() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a={"b": {"c": 1}})

    assert "a.b.c" in mapping


def test_contains_returns_false_for_missing_top_level_key() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1)

    assert "missing" not in mapping


def test_contains_returns_false_for_missing_nested_key() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a={"b": 1})

    assert "a.missing" not in mapping


def test_contains_returns_false_for_non_string_key() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1)

    assert 42 not in mapping
    assert None not in mapping


def test_get_returns_top_level_value() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1)

    assert mapping.get("a") == 1


def test_get_returns_nested_value_via_dotted_key() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a={"b": {"c": 42}})

    assert mapping.get("a.b.c") == 42


def test_get_returns_none_when_missing() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping()

    assert mapping.get("missing") is None


def test_get_returns_default_when_missing() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping()

    assert mapping.get("missing", default=99) == 99


def test_get_returns_default_when_nested_key_missing() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a={"b": 1})

    assert mapping.get("a.missing", default=99) == 99


def test_pop_removes_and_returns_top_level_value() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1, b=2)

    assert mapping.pop("a") == 1
    assert "a" not in mapping
    assert mapping["b"] == 2


def test_pop_removes_and_returns_nested_value() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a={"b": {"c": 42, "d": 1}})

    assert mapping.pop("a.b.c") == 42
    assert "a.b.c" not in mapping
    assert mapping["a.b.d"] == 1


def test_pop_returns_default_when_missing() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping()

    assert mapping.pop("missing", 99) == 99


def test_pop_returns_default_when_nested_key_missing() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a={"b": 1})

    assert mapping.pop("a.missing", 99) == 99


def test_popitem_removes_and_returns_top_level_item() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1)

    key, value = mapping.popitem()

    assert key == "a"
    assert value == 1
    assert len(mapping) == 0


def test_clear_empties_the_mapping() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1, b={"c": 2})

    mapping.clear()

    assert len(mapping) == 0
    assert list(mapping) == []


def test_update_merges_top_level_keys() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1)

    mapping.update({"b": 2, "c": 3})

    assert mapping["a"] == 1
    assert mapping["b"] == 2
    assert mapping["c"] == 3


def test_update_accepts_keyword_arguments() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1)

    mapping.update(b=2, c=3)

    assert mapping["b"] == 2
    assert mapping["c"] == 3


def test_setdefault_returns_existing_value() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1)

    assert mapping.setdefault("a", 99) == 1
    assert mapping["a"] == 1


def test_setdefault_sets_and_returns_default_when_missing() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping()

    assert mapping.setdefault("a", 42) == 42
    assert mapping["a"] == 42


def test_getitem_raises_key_error_when_intermediate_is_not_dict() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1)

    with pytest.raises(KeyError):
        mapping["a.b"]


def test_contains_returns_false_when_intermediate_is_not_dict() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1)

    assert "a.b" not in mapping


def test_get_returns_default_when_intermediate_is_not_dict() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1)

    assert mapping.get("a.b", default=99) == 99


def test_pop_returns_default_when_intermediate_is_not_dict() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1)

    assert mapping.pop("a.b", 99) == 99
    assert mapping["a"] == 1


def test_delitem_raises_key_error_when_intermediate_is_not_dict() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1)

    with pytest.raises(KeyError):
        del mapping["a.b"]


def test_setitem_raises_type_error_when_intermediate_is_not_dict() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1)

    with pytest.raises(TypeError):
        mapping["a.b"] = 2

    assert mapping["a"] == 1


def test_equality_with_matching_dict() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1, b=2)

    assert mapping == {"a": 1, "b": 2}


def test_supports_dict_conversion() -> None:
    mapping: DeepMutableMapping[int] = DeepMutableMapping(a=1, b=2)

    assert dict(mapping) == {"a": 1, "b": 2}
