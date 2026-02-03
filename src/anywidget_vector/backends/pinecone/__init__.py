"""Pinecone backend adapter.

Query Format (JSON):
    # Similarity search
    {"vector": [0.1, 0.2, ...], "topK": 10}

    # With filter
    {"vector": [...], "filter": {"category": {"$eq": "tech"}}, "topK": 10}

    # With namespace
    {"vector": [...], "topK": 10, "namespace": "my-namespace"}

    # Fetch by IDs
    {"ids": ["id1", "id2"]}

Filter operators: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin
"""

from anywidget_vector.backends.pinecone.converter import build_filter, to_points

__all__ = ["to_points", "build_filter"]
