"""Vector database backend adapters.

Each backend has its own query format matching its native API:
- Qdrant: JSON with vector, filter, limit
- Pinecone: JSON with vector, filter, topK
- Weaviate: GraphQL
- Chroma: Python dict (query_embeddings, where, n_results)
- LanceDB: SQL-like expressions
- Grafeo: Grafeo query format
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class VectorBackend(Protocol):
    """Protocol for vector database backends."""

    name: str
    side: str  # "browser" or "python"
    query_language: str  # e.g., "json", "graphql", "sql", "python"

    def execute(self, query: str, config: dict[str, Any]) -> list[dict[str, Any]]:
        """Execute a query and return points."""
        ...


# Backend registry with metadata
BACKENDS: dict[str, dict[str, Any]] = {
    "qdrant": {
        "name": "Qdrant",
        "side": "browser",
        "query_language": "json",
        "placeholder": '{"vector": [...], "limit": 10}',
        "help": "JSON: vector, filter, limit, recommend, ids",
    },
    "pinecone": {
        "name": "Pinecone",
        "side": "browser",
        "query_language": "json",
        "placeholder": '{"vector": [...], "topK": 10}',
        "help": "JSON: vector, filter, topK, namespace",
    },
    "weaviate": {
        "name": "Weaviate",
        "side": "browser",
        "query_language": "graphql",
        "placeholder": "{ Get { Class(limit: 10) { ... } } }",
        "help": "GraphQL with nearVector, nearText, where",
    },
    "chroma": {
        "name": "Chroma",
        "side": "python",
        "query_language": "dict",
        "placeholder": '{"query_embeddings": [...], "n_results": 10}',
        "help": "Dict: query_embeddings, where, n_results",
    },
    "lancedb": {
        "name": "LanceDB",
        "side": "python",
        "query_language": "sql",
        "placeholder": "category = 'tech' AND year > 2020",
        "help": "SQL WHERE clause for filtering",
    },
    "grafeo": {
        "name": "Grafeo",
        "side": "python",
        "query_language": "grafeo",
        "placeholder": "MATCH (n:Vector) RETURN n LIMIT 10",
        "help": "Grafeo query language",
    },
}


def get_backend_info(name: str) -> dict[str, Any] | None:
    """Get backend configuration by name."""
    return BACKENDS.get(name)


def is_browser_backend(name: str) -> bool:
    """Check if backend runs in browser."""
    info = BACKENDS.get(name)
    return info is not None and info.get("side") == "browser"


def is_python_backend(name: str) -> bool:
    """Check if backend runs in Python."""
    info = BACKENDS.get(name)
    return info is not None and info.get("side") == "python"


def get_query_placeholder(name: str) -> str:
    """Get example query placeholder for backend."""
    info = BACKENDS.get(name)
    return info.get("placeholder", "") if info else ""


def get_query_help(name: str) -> str:
    """Get query help text for backend."""
    info = BACKENDS.get(name)
    return info.get("help", "") if info else ""
