"""LanceDB result conversion."""

from __future__ import annotations

from typing import Any


def to_points(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert LanceDB results to points format."""
    points = []

    for i, row in enumerate(results):
        point: dict[str, Any] = {"id": str(row.get("id", f"point_{i}"))}

        # Distance -> score
        if "_distance" in row:
            point["score"] = 1 / (1 + row["_distance"])

        # Find vector field
        vector = None
        for key in ("vector", "embedding", "embeddings", "_vec"):
            if key in row and row[key] is not None:
                vector = row[key]
                break

        if vector is not None:
            vec = list(vector) if hasattr(vector, "__iter__") else [vector]
            point["x"] = float(vec[0]) if len(vec) > 0 else 0
            point["y"] = float(vec[1]) if len(vec) > 1 else 0
            point["z"] = float(vec[2]) if len(vec) > 2 else 0
            point["vector"] = vec

        # Add other fields
        skip_keys = {"id", "vector", "embedding", "embeddings", "_vec", "_distance"}
        for k, v in row.items():
            if k not in skip_keys:
                point[k] = v

        points.append(point)

    return points


def build_where(conditions: list[tuple[str, str, Any]]) -> str:
    """Build SQL WHERE clause from conditions.

    Returns SQL string compatible with LanceDB.
    """
    if not conditions:
        return ""

    parts = []
    for field, op, value in conditions:
        if op == "~":
            # LIKE for partial match
            parts.append(f"{field} LIKE '%{value}%'")
        elif op == ":":
            # IN for array contains
            if isinstance(value, list):
                values = ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in value)
            else:
                values = f"'{value}'" if isinstance(value, str) else str(value)
            parts.append(f"{field} IN ({values})")
        else:
            # Standard operators
            if isinstance(value, str):
                parts.append(f"{field} {op} '{value}'")
            else:
                parts.append(f"{field} {op} {value}")

    return " AND ".join(parts)
