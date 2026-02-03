"""Grafeo Python client."""

from __future__ import annotations

from typing import Any

from anywidget_vector.backends.grafeo.converter import to_points


def execute_query(
    client: Any,
    query: str,
) -> list[dict[str, Any]]:
    """Execute query against Grafeo.

    Args:
        client: Grafeo client/session object
        query: Grafeo query string

    Returns:
        List of points
    """
    # Execute the query - actual API depends on Grafeo implementation
    if hasattr(client, "query"):
        results = client.query(query)
    elif hasattr(client, "run"):
        results = client.run(query)
    elif hasattr(client, "execute"):
        results = client.execute(query)
    else:
        raise ValueError("Grafeo client must have query(), run(), or execute() method")

    return to_points(results)
