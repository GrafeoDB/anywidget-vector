"""Grafeo result conversion."""

from __future__ import annotations

from typing import Any


def to_points(results: Any) -> list[dict[str, Any]]:
    """Convert Grafeo results to points format."""
    # Handle different result types
    if hasattr(results, "to_dict"):
        results = results.to_dict("records")
    elif hasattr(results, "records"):
        results = [dict(r) for r in results.records()]
    elif not isinstance(results, list):
        results = list(results)

    points = []
    for i, item in enumerate(results):
        if isinstance(item, dict):
            point: dict[str, Any] = {"id": str(item.get("id", f"point_{i}"))}

            # Look for vector/embedding
            vector = item.get("vector") or item.get("embedding")
            if vector:
                vec = list(vector) if hasattr(vector, "__iter__") else [vector]
                point["x"] = float(vec[0]) if len(vec) > 0 else 0
                point["y"] = float(vec[1]) if len(vec) > 1 else 0
                point["z"] = float(vec[2]) if len(vec) > 2 else 0
                point["vector"] = vec
            else:
                point["x"] = float(item.get("x", 0))
                point["y"] = float(item.get("y", 0))
                point["z"] = float(item.get("z", 0))

            # Add all other fields
            for k, v in item.items():
                if k not in ("id", "vector", "embedding", "x", "y", "z"):
                    point[k] = v

            points.append(point)
        else:
            # Raw value
            points.append({"id": f"point_{i}", "data": item, "x": 0, "y": 0, "z": 0})

    return points
