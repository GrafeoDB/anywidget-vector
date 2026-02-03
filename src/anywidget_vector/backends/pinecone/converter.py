"""Pinecone result conversion and filter building."""

from __future__ import annotations

from typing import Any


def to_points(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert Pinecone response to points format."""
    matches = response.get("matches") or []

    points = []
    for m in matches:
        point: dict[str, Any] = {"id": m.get("id", "")}

        if "score" in m:
            point["score"] = m["score"]

        values = m.get("values", [])
        metadata = m.get("metadata", {})

        if values:
            point["x"] = float(values[0]) if len(values) > 0 else 0
            point["y"] = float(values[1]) if len(values) > 1 else 0
            point["z"] = float(values[2]) if len(values) > 2 else 0
            point["vector"] = values
        else:
            point["x"] = float(metadata.get("x", 0))
            point["y"] = float(metadata.get("y", 0))
            point["z"] = float(metadata.get("z", 0))

        point.update(metadata)
        points.append(point)

    return points


def build_filter(conditions: list[tuple[str, str, Any]]) -> dict[str, Any]:
    """Build Pinecone filter from conditions.

    Pinecone uses MongoDB-style operators: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin
    """
    filter_dict = {}

    op_map = {
        "=": "$eq",
        "!=": "$ne",
        ">": "$gt",
        ">=": "$gte",
        "<": "$lt",
        "<=": "$lte",
        ":": "$in",  # Array contains
    }

    for field, op, value in conditions:
        pinecone_op = op_map.get(op)
        if pinecone_op:
            if pinecone_op == "$in" and not isinstance(value, list):
                value = [value]
            filter_dict[field] = {pinecone_op: value}

    return filter_dict
