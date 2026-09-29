"""Inference authorization and a dependency-free JSON Schema subset validator."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json
from math import isfinite
from typing import Any

from .models import AgentDefinition, AgentSession, BrainOperation, InferenceRequest


class OutputValidationError(ValueError):
    pass


def validate_schema_definition(schema: dict[str, Any]) -> None:
    supported = {
        "$schema", "title", "description", "type", "enum", "required", "properties", "additionalProperties",
        "items", "minItems", "maxItems", "minLength", "maxLength", "minimum", "maximum",
    }
    if not isinstance(schema, dict):
        raise ValueError("Output schemas must be JSON Schema objects.")
    unsupported = set(schema) - supported
    if unsupported:
        raise ValueError(f"Unsupported JSON Schema keyword(s): {', '.join(sorted(unsupported))}.")
    expected = schema.get("type")
    valid_types = {"object", "array", "string", "integer", "number", "boolean", "null"}
    if expected is not None and (not isinstance(expected, str) or expected not in valid_types):
        raise ValueError(f"Unsupported JSON Schema type: {expected}")
    if "enum" in schema and (not isinstance(schema["enum"], list) or not schema["enum"]):
        raise ValueError("Schema enum must be a non-empty list.")
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    if not isinstance(required, list) or any(not isinstance(name, str) for name in required):
        raise ValueError("Schema required must be a list of property names.")
    if not isinstance(properties, dict) or any(not isinstance(name, str) for name in properties):
        raise ValueError("Schema properties must be an object keyed by property names.")
    for name, child in properties.items():
        validate_schema_definition(child)
    items = schema.get("items")
    if items is not None:
        validate_schema_definition(items)
    additional = schema.get("additionalProperties", True)
    if not isinstance(additional, bool):
        validate_schema_definition(additional)
    for key in ("minItems", "maxItems", "minLength", "maxLength"):
        value = schema.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise ValueError(f"Schema {key} must be a non-negative integer.")
    for key in ("minimum", "maximum"):
        value = schema.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value)):
            raise ValueError(f"Schema {key} must be a finite number.")
    for minimum_key, maximum_key in (("minItems", "maxItems"), ("minLength", "maxLength"), ("minimum", "maximum")):
        if minimum_key in schema and maximum_key in schema and schema[minimum_key] > schema[maximum_key]:
            raise ValueError(f"Schema {minimum_key} cannot exceed {maximum_key}.")


def authorize_inference(agent: AgentDefinition, session: AgentSession, request: InferenceRequest) -> None:
    if agent.agent_id != request.agent_id or session.agent_id != request.agent_id:
        raise PermissionError("Inference agent identity does not match the session.")
    if agent.sector != request.sector or session.sector != request.sector:
        raise PermissionError("Inference sector does not match the session.")
    if session.task_id != request.task_id:
        raise PermissionError("Inference task does not match the session.")
    if request.operation not in agent.allowed_operations or request.operation not in session.allowed_operations:
        raise PermissionError("Agent is not authorized for this operation.")
    if request.max_tokens > agent.max_tokens_per_task or request.max_tokens > session.token_limit:
        raise PermissionError("Inference token limit exceeds the task or session budget.")
    if request.max_cost.currency != agent.max_cost_per_task.currency or request.max_cost.currency != session.cost_limit.currency:
        raise PermissionError("Inference budget currency does not match the agent policy.")
    if request.max_cost.amount > agent.max_cost_per_task.amount or request.max_cost.amount > session.cost_limit.amount:
        raise PermissionError("Inference cost limit exceeds the task or session budget.")


def validate_output(value: Any, schema: dict[str, Any]) -> None:
    """Validate common JSON Schema types, required fields, enums, and bounds."""
    _validate(value, schema, "$")


def _validate(value: Any, schema: dict[str, Any], path: str) -> None:
    expected = schema.get("type")
    valid_types = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool) and isfinite(item),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    if expected is not None:
        predicate = valid_types.get(expected)
        if predicate is None:
            raise ValueError(f"Unsupported schema type: {expected}")
        if not predicate(value):
            raise OutputValidationError(f"{path} must be {expected}.")
    if "enum" in schema and value not in schema["enum"]:
        raise OutputValidationError(f"{path} is not an allowed value.")
    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = [name for name in required if name not in value]
        if missing:
            raise OutputValidationError(f"{path} is missing required properties: {', '.join(missing)}.")
        properties = schema.get("properties", {})
        extra = set(value) - set(properties)
        additional = schema.get("additionalProperties", True)
        if additional is False:
            if extra:
                raise OutputValidationError(f"{path} contains unexpected properties: {', '.join(sorted(extra))}.")
        for name, child in properties.items():
            if name in value:
                _validate(value[name], child, f"{path}.{name}")
        if isinstance(additional, dict):
            for name in extra:
                _validate(value[name], additional, f"{path}.{name}")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise OutputValidationError(f"{path} contains too few items.")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise OutputValidationError(f"{path} contains too many items.")
        if "items" in schema:
            for index, item in enumerate(value):
                _validate(item, schema["items"], f"{path}[{index}]")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise OutputValidationError(f"{path} is too short.")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise OutputValidationError(f"{path} is too long.")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise OutputValidationError(f"{path} is below its minimum.")
        if "maximum" in schema and value > schema["maximum"]:
            raise OutputValidationError(f"{path} exceeds its maximum.")


def canonical_json(value: Any) -> str:
    def normalize(item: Any) -> Any:
        if is_dataclass(item):
            return normalize(asdict(item))
        if isinstance(item, Enum):
            return item.value
        if isinstance(item, datetime):
            if item.tzinfo is None:
                raise TypeError("Audit datetimes must be timezone-aware.")
            return item.isoformat()
        if item is None or isinstance(item, (str, bool, int)):
            return item
        if isinstance(item, float):
            if not isfinite(item):
                raise TypeError("Audit values cannot contain non-finite floats.")
            return item
        if isinstance(item, (list, tuple)):
            return [normalize(entry) for entry in item]
        if isinstance(item, dict) and all(isinstance(key, str) for key in item):
            return {key: normalize(item[key]) for key in sorted(item)}
        raise TypeError(f"Unsupported audit value: {type(item).__name__}")

    return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_hash(value: Any) -> str:
    return "sha256:" + sha256(canonical_json(value).encode("utf-8")).hexdigest()
