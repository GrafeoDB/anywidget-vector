"""Weaviate result conversion and filter building."""

from __future__ import annotations

from typing import Any


def to_points(response: dict[str, Any], class_name: str) -> list[dict[str, Any]]:
    """Convert Weaviate GraphQL response to points format."""
    data = response.get("data", {}).get("Get", {}).get(class_name, [])

    points = []
    for i, item in enumerate(data):
        additional = item.get("_additional", {})
        point: dict[str, Any] = {"id": additional.get("id", f"point_{i}")}

        if "distance" in additional:
            point["score"] = 1 - additional["distance"]

        vector = additional.get("vector", [])
        if vector:
            point["x"] = float(vector[0]) if len(vector) > 0 else 0
            point["y"] = float(vector[1]) if len(vector) > 1 else 0
            point["z"] = float(vector[2]) if len(vector) > 2 else 0
            point["vector"] = vector

        # Add all other fields except _additional
        for k, v in item.items():
            if k != "_additional":
                point[k] = v

        points.append(point)

    return points


def build_where(conditions: list[tuple[str, str, Any]]) -> dict[str, Any]:
    """Build Weaviate where filter from conditions.

    Weaviate operators: Equal, NotEqual, GreaterThan, GreaterThanEqual,
                        LessThan, LessThanEqual, Like, ContainsAny
    """
    op_map = {
        "=": "Equal",
        "!=": "NotEqual",
        ">": "GreaterThan",
        ">=": "GreaterThanEqual",
        "<": "LessThan",
        "<=": "LessThanEqual",
        "~": "Like",
        ":": "ContainsAny",
    }

    if len(conditions) == 0:
        return {}

    if len(conditions) == 1:
        field, op, value = conditions[0]
        return _single_condition(field, op_map.get(op, "Equal"), value)

    # Multiple conditions: AND them together
    operands = [_single_condition(f, op_map.get(o, "Equal"), v) for f, o, v in conditions]
    return {"operator": "And", "operands": operands}


def _single_condition(field: str, operator: str, value: Any) -> dict[str, Any]:
    """Build single where condition."""
    result = {"path": [field], "operator": operator}

    if isinstance(value, str):
        result["valueText"] = value
    elif isinstance(value, bool):
        result["valueBoolean"] = value
    elif isinstance(value, int):
        result["valueInt"] = value
    elif isinstance(value, float):
        result["valueNumber"] = value
    elif isinstance(value, list):
        result["valueText"] = value  # For ContainsAny

    return result
