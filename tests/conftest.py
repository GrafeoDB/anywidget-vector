"""Shared fixtures."""

from __future__ import annotations

from typing import Any

import pytest

from tests.support import DOCS


@pytest.fixture
def grafeo_db() -> Any:
    """In-memory GrafeoDB with :Doc nodes (name, embedding, cat), no index yet."""
    import grafeo

    db = grafeo.GrafeoDB()
    for name, embedding, cat in DOCS:
        db.create_node(["Doc"], {"name": name, "embedding": embedding, "cat": cat})
    return db
