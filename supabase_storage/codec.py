"""Strict JSON encoding and decoding for persisted domain dataclasses."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from math import isfinite
import types
from typing import Any, Literal, TypeVar, Union, get_args, get_origin, get_type_hints


T = TypeVar("T")


def to_json_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: to_json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("Persisted JSON objects require string keys.")
        return {key: to_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_json_value(item) for item in value]
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("Persisted JSON numbers must be finite.")
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f"Unsupported persisted value: {type(value).__name__}")


def from_json_value(value: Any, expected_type: Any) -> Any:
    if expected_type is Any:
        return value
    origin = get_origin(expected_type)
    args = get_args(expected_type)
    if origin in (Union, types.UnionType):
        if value is None and type(None) in args:
            return None
        failures: list[Exception] = []
        for candidate in args:
            if candidate is type(None):
                continue
            try:
                return from_json_value(value, candidate)
            except (TypeError, ValueError, KeyError) as error:
                failures.append(error)
        raise ValueError(f"Value does not match union type {expected_type!r}.") from (failures[-1] if failures else None)
    if origin is Literal:
        if value not in args:
            raise ValueError(f"Invalid literal value for {expected_type!r}.")
        return value
    if origin in (list, tuple, set, frozenset):
        item_type = args[0] if args else Any
        items = [from_json_value(item, item_type) for item in value]
        if origin is tuple:
            return tuple(items)
        if origin is set:
            return set(items)
        if origin is frozenset:
            return frozenset(items)
        return items
    if origin is dict:
        key_type, value_type = args if args else (Any, Any)
        return {
            from_json_value(key, key_type): from_json_value(item, value_type)
            for key, item in value.items()
        }
    if isinstance(expected_type, type) and issubclass(expected_type, Enum):
        return expected_type(value)
    if expected_type is datetime:
        return datetime.fromisoformat(value)
    if expected_type is date:
        return date.fromisoformat(value)
    if isinstance(expected_type, type) and is_dataclass(expected_type):
        hints = get_type_hints(expected_type)
        declared = {field.name for field in fields(expected_type) if field.init}
        return expected_type(**{
            key: from_json_value(item, hints.get(key, Any))
            for key, item in value.items()
            if key in declared
        })
    if expected_type in (str, int, float, bool):
        if expected_type is int and isinstance(value, bool):
            raise TypeError("Boolean is not an integer domain value.")
        if expected_type is float and isinstance(value, int) and not isinstance(value, bool):
            return float(value)
        if not isinstance(value, expected_type):
            raise TypeError(f"Expected {expected_type.__name__}, got {type(value).__name__}.")
    return value


def decode_model(payload: Any, model_type: type[T]) -> T:
    if not isinstance(payload, dict):
        raise TypeError("Persisted domain payload must be a JSON object.")
    model = from_json_value(payload, model_type)
    if not isinstance(model, model_type):
        raise TypeError(f"Decoded value is not a {model_type.__name__}.")
    return model
