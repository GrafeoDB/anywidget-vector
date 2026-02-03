"""Chroma backend adapter.

Query Format (dict):
    # Query by embeddings
    {"query_embeddings": [[0.1, 0.2, ...]], "n_results": 10}

    # With where filter
    {
        "query_embeddings": [[0.1, 0.2, ...]],
        "where": {"category": "tech"},
        "n_results": 10
    }

    # Get by IDs
    {"ids": ["id1", "id2"]}

    # Get with filter only
    {"where": {"category": "tech"}, "limit": 100}

Where operators: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin
Combined: $and, $or
"""

from anywidget_vector.backends.chroma.client import execute_query
from anywidget_vector.backends.chroma.converter import build_where, to_points

__all__ = ["to_points", "build_where", "execute_query"]
