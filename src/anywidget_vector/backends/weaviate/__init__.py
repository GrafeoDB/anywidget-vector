"""Weaviate backend adapter.

Query Format (GraphQL):
    # Get all with limit
    { Get { Article(limit: 10) { title _additional { id vector } } } }

    # Near vector search
    {
      Get {
        Article(nearVector: {vector: [0.1, 0.2, ...]}, limit: 10) {
          title
          _additional { id vector distance }
        }
      }
    }

    # With where filter
    {
      Get {
        Article(
          where: {path: ["category"], operator: Equal, valueText: "tech"}
          limit: 10
        ) { title _additional { id } }
      }
    }

    # Near text (requires text2vec module)
    { Get { Article(nearText: {concepts: ["AI"]}, limit: 10) { ... } } }
"""

from anywidget_vector.backends.weaviate.converter import build_where, to_points

__all__ = ["to_points", "build_where"]
