"""LanceDB Python client."""

from __future__ import annotations

import json
from typing import Any

from anywidget_vector.backends.lancedb.converter import to_points


def execute_query(
    table: Any,
    query: str | dict[str, Any],
) -> list[dict[str, Any]]:
    """Execute query against LanceDB table.

    Args:
        table: LanceDB table object
        query: Query dict or JSON string

    Returns:
        List of points
    """
    if isinstance(query, str):
        query = json.loads(query)

    limit = query.get("limit", 100)

    # Vector search
    if "vector" in query:
        search = table.search(query["vector"])
        if "where" in query:
            search = search.where(query["where"])
        results = search.limit(limit).to_list()
        return to_points(results)

    # Full-text search
    if "fts" in query:
        search = table.search(query["fts"], query_type="fts")
        if "where" in query:
            search = search.where(query["where"])
        results = search.limit(limit).to_list()
        return to_points(results)

    # Filter only
    if "where" in query:
        # Use pandas for filtered scan
        df = table.to_pandas()
        # Simple eval for WHERE clause (in production, use proper SQL parser)
        # For now, return all and let filter happen client-side
        results = df.head(limit).to_dict("records")
        return to_points(results)

    # Get all
    results = table.to_pandas().head(limit).to_dict("records")
    return to_points(results)
