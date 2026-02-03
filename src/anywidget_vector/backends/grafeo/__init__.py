"""Grafeo backend adapter.

Query Format (Grafeo Query Language):
    # Get vectors with limit
    MATCH (n:Vector) RETURN n LIMIT 10

    # Filter by property
    MATCH (n:Vector {category: "tech"}) RETURN n LIMIT 10

    # Vector similarity (placeholder - depends on Grafeo API)
    MATCH (n:Vector) WHERE similarity(n.embedding, $vector) > 0.8 RETURN n

    # Connected nodes
    MATCH (n:Vector)-[r]->(m) RETURN n, r, m LIMIT 10
"""

from anywidget_vector.backends.grafeo.client import execute_query
from anywidget_vector.backends.grafeo.converter import to_points

__all__ = ["to_points", "execute_query"]
