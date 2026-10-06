"""Grafeo backend adapter.

Query Format (GQL, one statement per query):
    # Get vectors with limit
    MATCH (n:Vector) RETURN n LIMIT 10

    # Filter by property
    MATCH (n:Vector {category: "tech"}) RETURN n LIMIT 10

    # k-nearest neighbors through the HNSW index (create it first)
    CREATE VECTOR INDEX vector_embedding ON :Vector(embedding) DIMENSION 3 METRIC 'cosine'
    CALL grafeo.search.vector('Vector', 'embedding', [0.1, 0.2, 0.3], 10) YIELD node_id, distance
    NEXT MATCH (n:Vector) WHERE id(n) = node_id RETURN n, distance ORDER BY distance

    # Similarity without an index
    MATCH (n:Vector) RETURN n, cosine_similarity(n.embedding, vector([0.1, 0.2, 0.3])) AS score
    ORDER BY score DESC LIMIT 10
"""

from anywidget_vector.backends.grafeo.client import execute_query
from anywidget_vector.backends.grafeo.converter import to_points

__all__ = ["execute_query", "to_points"]
