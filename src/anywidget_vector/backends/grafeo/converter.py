"""Grafeo result conversion.

Mirrors ``backends/grafeo/points.js`` (server and WASM backends), so a query
gives the same points in every Grafeo connection mode.

Engine value encoding (grafeo 0.5.44): a node is ``{"_id", "_labels", **properties}``,
a vector is a list of floats, and an unaliased column is named after its
expression (``n.embedding``, ``id(n)``). Coordinates come from explicit x/y/z
fields when present, otherwise from the first three vector components.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from typing import Any

_VECTOR_KEYS = frozenset({"vector", "embedding", "embeddings"})
_AXES = ("x", "y", "z")
_PROPERTY_COLUMN = re.compile(r"[A-Za-z_]\w*\.([A-Za-z_]\w*)")
_ID_COLUMN = re.compile(r"id\(\s*[A-Za-z_]\w*\s*\)", re.IGNORECASE)


def column_key(column: str) -> str:
    """Map a result column to a point key: ``n.embedding`` -> ``embedding``, ``id(n)`` -> ``id``."""
    if match := _PROPERTY_COLUMN.fullmatch(column):
        return match.group(1)
    if _ID_COLUMN.fullmatch(column):
        return "id"
    return column


def is_node(value: Any) -> bool:
    """True for a Grafeo node value (a mapping with ``_id`` and ``_labels``)."""
    return isinstance(value, Mapping) and "_id" in value and isinstance(value.get("_labels"), list | tuple)


def _as_vector(value: Any) -> list[float] | None:
    if value is None or isinstance(value, str | bytes | Mapping) or not isinstance(value, Iterable):
        return None
    try:
        return [float(v) for v in value]
    except (TypeError, ValueError):
        return None


def _finite(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _row_fields(row: Mapping[str, Any]) -> list[tuple[str, Any]]:
    """Flatten a row into (key, value) fields, expanding node values into their properties."""
    fields: list[tuple[str, Any]] = []
    column_keys: set[str] = set()
    for column, value in row.items():
        if is_node(value):
            fields.extend((k, v) for k, v in value.items() if not str(k).startswith("_"))
            # The engine identity wins over a user property named `id`
            fields.append(("id", value["_id"]))
            fields.append(("labels", list(value["_labels"])))
            continue
        # `RETURN a.name, b.name`: keep the second one under its full column name
        key = column_key(str(column))
        fields.append((str(column) if key in column_keys else key, value))
        column_keys.add(key)
    return fields


def row_to_point(row: Mapping[str, Any], index: int) -> dict[str, Any]:
    """Convert one result row (column -> value) into a point."""
    point: dict[str, Any] = {"id": f"point_{index}"}
    vector: list[float] | None = None

    for key, value in _row_fields(row):
        if value is None:
            continue
        if key in ("id", "ID"):
            point["id"] = str(value)
        elif key in _VECTOR_KEYS and (as_vector := _as_vector(value)) is not None:
            if vector is None:
                vector = as_vector
        elif key in _AXES:
            point[key] = _finite(value)
        else:
            point[key] = value

    if vector is not None:
        point["vector"] = vector
    for i, axis in enumerate(_AXES):
        if axis not in point:
            point[axis] = _finite(vector[i]) if vector is not None and len(vector) > i else 0.0
    return point


def to_points(results: Any) -> list[dict[str, Any]]:
    """Convert Grafeo results to points format.

    Accepts a ``grafeo.QueryResult`` (iterates as one dict per row), a pandas
    DataFrame, an object with ``records()``, or any iterable of row mappings.
    """
    if hasattr(results, "to_dict"):
        rows = results.to_dict("records")
    elif hasattr(results, "records"):
        rows = [dict(r) for r in results.records()]
    else:
        rows = list(results)

    points = []
    for i, item in enumerate(rows):
        if isinstance(item, Mapping):
            points.append(row_to_point(item, i))
        else:
            points.append({"id": f"point_{i}", "data": item, "x": 0.0, "y": 0.0, "z": 0.0})
    return points
