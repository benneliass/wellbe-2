"""Local check of the small JSON Schema subset this caller sends."""

from __future__ import annotations

from collections.abc import Mapping


def matches(schema: Mapping[str, object], value: object) -> bool:
    type_name = schema.get("type")
    if isinstance(type_name, list):
        return any(
            matches({**schema, "type": item}, value) for item in type_name if isinstance(item, str)
        )
    if type_name == "null":
        return value is None
    if type_name == "string":
        if not isinstance(value, str):
            return False
        enum = schema.get("enum")
        return not isinstance(enum, list) or value in enum
    if type_name == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if type_name == "array":
        return _matches_array(schema, value)
    if type_name == "object":
        return _matches_object(schema, value)
    return False


def _matches_array(schema: Mapping[str, object], value: object) -> bool:
    if not isinstance(value, list):
        return False
    minimum = schema.get("minItems")
    maximum = schema.get("maxItems")
    if isinstance(minimum, int) and len(value) < minimum:
        return False
    if isinstance(maximum, int) and len(value) > maximum:
        return False
    item_schema = schema.get("items")
    if isinstance(item_schema, dict):
        return all(matches(item_schema, item) for item in value)
    return True


def _matches_object(schema: Mapping[str, object], value: object) -> bool:
    if not isinstance(value, dict):
        return False
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        properties = {}
    required = schema.get("required")
    if isinstance(required, list) and any(key not in value for key in required):
        return False
    if schema.get("additionalProperties") is False and any(key not in properties for key in value):
        return False
    for key, prop in properties.items():
        if key in value and isinstance(prop, dict) and not matches(prop, value[key]):
            return False
    return True
