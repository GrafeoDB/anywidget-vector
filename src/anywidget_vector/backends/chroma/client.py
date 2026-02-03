"""Chroma Python client."""

from __future__ import annotations

import json
from typing import Any

from anywidget_vector.backends.chroma.converter import to_points


def execute_query(
    collection: Any,
    query: str | dict[str, Any],
) -> list[dict[str, Any]]:
    """Execute query against Chroma collection.

    Args:
        collection: Chroma collection object
        query: Query dict or JSON string

    Returns:
        List of points
    """
    if isinstance(query, str):
        query = json.loads(query)

    # Get by IDs
    if "ids" in query:
        response = collection.get(
            ids=query["ids"],
            include=["embeddings", "metadatas", "documents"],
        )
        return to_points(response)

    # Query by embeddings
    if "query_embeddings" in query:
        response = collection.query(
            query_embeddings=query["query_embeddings"],
            n_results=query.get("n_results", 10),
            where=query.get("where"),
            where_document=query.get("where_document"),
            include=["embeddings", "metadatas", "documents", "distances"],
        )
        return to_points(response)

    # Get with filter
    if "where" in query:
        response = collection.get(
            where=query["where"],
            limit=query.get("limit", 100),
            include=["embeddings", "metadatas", "documents"],
        )
        return to_points(response)

    # Get all (with limit)
    response = collection.get(
        limit=query.get("limit", 100),
        include=["embeddings", "metadatas", "documents"],
    )
    return to_points(response)
