"""LanceDB backend adapter.

Query Format:
    # Vector search (pass vector separately)
    {"vector": [0.1, 0.2, ...], "limit": 10}

    # With SQL filter
    {"vector": [...], "where": "category = 'tech' AND year > 2020", "limit": 10}

    # Filter only (no vector)
    {"where": "category = 'tech'", "limit": 100}

    # Full-text search
    {"fts": "search query", "limit": 10}

SQL WHERE supports: =, !=, <, >, <=, >=, AND, OR, IN, LIKE, IS NULL, IS NOT NULL
"""

from anywidget_vector.backends.lancedb.client import execute_query
from anywidget_vector.backends.lancedb.converter import to_points

__all__ = ["to_points", "execute_query"]
