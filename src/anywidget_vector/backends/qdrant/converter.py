"""Qdrant result conversion and filter building."""

from __future__ import annotations

from typing import Any


def to_points(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert Qdrant response to points format.

    Args:
        response: Qdrant API response

    Returns:
        List of point dicts with id, x, y, z, and metadata
    """
    results = response.get("result") or response.get("points") or []

    points = []
    for r in results:
        point: dict[str, Any] = {"id": str(r.get("id", ""))}

        if "score" in r:
            point["score"] = r["score"]

        vector = r.get("vector")
        payload = r.get("payload", {})

        if vector:
            point["x"] = float(vector[0]) if len(vector) > 0 else 0
            point["y"] = float(vector[1]) if len(vector) > 1 else 0
            point["z"] = float(vector[2]) if len(vector) > 2 else 0
            point["vector"] = vector
        else:
            point["x"] = float(payload.get("x", 0))
            point["y"] = float(payload.get("y", 0))
            point["z"] = float(payload.get("z", 0))

        point.update(payload)
        points.append(point)

    return points


def build_filter(conditions: list[tuple[str, str, Any]]) -> dict[str, Any]:
    """Build Qdrant filter from conditions.

    Args:
        conditions: List of (field, operator, value) tuples
            Operators: =, !=, >, >=, <, <=, ~, :

    Returns:
        Qdrant filter dict

    Example:
        >>> build_filter([("category", "=", "tech"), ("year", ">", 2020)])
        {"must": [
            {"key": "category", "match": {"value": "tech"}},
            {"key": "year", "range": {"gt": 2020}}
        ]}
    """
    must = []

    for field, op, value in conditions:
        if op == "=":
            must.append({"key": field, "match": {"value": value}})
        elif op == "!=":
            # Qdrant doesn't have direct != so we use must_not
            continue  # Handle separately
        elif op == ">":
            must.append({"key": field, "range": {"gt": value}})
        elif op == ">=":
            must.append({"key": field, "range": {"gte": value}})
        elif op == "<":
            must.append({"key": field, "range": {"lt": value}})
        elif op == "<=":
            must.append({"key": field, "range": {"lte": value}})
        elif op == "~":
            must.append({"key": field, "match": {"text": value}})
        elif op == ":":
            must.append({"key": field, "match": {"any": [value]}})

    return {"must": must} if must else {}
