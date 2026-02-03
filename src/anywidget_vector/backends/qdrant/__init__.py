"""Qdrant backend adapter.

Query Format (JSON):
    # Similarity search
    {"vector": [0.1, 0.2, 0.3], "limit": 10}

    # With filter
    {
        "vector": [0.1, 0.2, 0.3],
        "filter": {"must": [{"key": "category", "match": {"value": "tech"}}]},
        "limit": 10
    }

    # Recommend by ID
    {"recommend": {"positive": ["point_123"]}, "limit": 10}

    # Get by IDs
    {"ids": ["point_1", "point_2"]}

    # Scroll/filter only
    {"filter": {"must": [...]}, "limit": 100}
"""

from anywidget_vector.backends.qdrant.converter import to_points, build_filter

__all__ = ["to_points", "build_filter"]
