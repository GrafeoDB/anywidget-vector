"""Chroma result conversion and filter building."""

from __future__ import annotations

from typing import Any


def to_points(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert Chroma response to points format."""
    # Handle query results (nested lists) vs get results (flat lists)
    is_query = "distances" in response

    ids = response.get("ids", [[]])[0] if is_query else response.get("ids", [])
    embeddings = response.get("embeddings", [[]])[0] if is_query else response.get("embeddings", [])
    metadatas = response.get("metadatas", [[]])[0] if is_query else response.get("metadatas", [])
    distances = response.get("distances", [[]])[0] if is_query else []
    documents = response.get("documents", [[]])[0] if is_query else response.get("documents", [])

    points = []
    for i, id_ in enumerate(ids):
        point: dict[str, Any] = {"id": str(id_)}

        # Score from distance (invert since distance = dissimilarity)
        if distances and i < len(distances):
            point["score"] = 1 / (1 + distances[i])

        # Embeddings -> coordinates
        if embeddings and i < len(embeddings) and embeddings[i]:
            vec = embeddings[i]
            point["x"] = float(vec[0]) if len(vec) > 0 else 0
            point["y"] = float(vec[1]) if len(vec) > 1 else 0
            point["z"] = float(vec[2]) if len(vec) > 2 else 0
            point["vector"] = vec

        # Document content
        if documents and i < len(documents) and documents[i]:
            point["document"] = documents[i]

        # Metadata
        if metadatas and i < len(metadatas) and metadatas[i]:
            point.update(metadatas[i])

        points.append(point)

    return points


def build_where(conditions: list[tuple[str, str, Any]]) -> dict[str, Any]:
    """Build Chroma where filter from conditions.

    Chroma uses MongoDB-style operators: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin
    """
    op_map = {
        "=": "$eq",
        "!=": "$ne",
        ">": "$gt",
        ">=": "$gte",
        "<": "$lt",
        "<=": "$lte",
        ":": "$in",
    }

    if len(conditions) == 0:
        return {}

    if len(conditions) == 1:
        field, op, value = conditions[0]
        chroma_op = op_map.get(op, "$eq")
        if chroma_op == "$eq":
            return {field: value}
        if chroma_op == "$in" and not isinstance(value, list):
            value = [value]
        return {field: {chroma_op: value}}

    # Multiple conditions: $and
    and_list = []
    for field, op, value in conditions:
        chroma_op = op_map.get(op, "$eq")
        if chroma_op == "$eq":
            and_list.append({field: value})
        else:
            if chroma_op == "$in" and not isinstance(value, list):
                value = [value]
            and_list.append({field: {chroma_op: value}})

    return {"$and": and_list}
