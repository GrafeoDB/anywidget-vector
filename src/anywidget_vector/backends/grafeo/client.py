"""Grafeo Python client."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from anywidget_vector.backends.grafeo.converter import to_points


def _query_method(client: Any) -> Callable[[str], Any]:
    # `execute` must win: on grafeo.GrafeoDB, `query()` returns a QueryBuilder, not results.
    for name in ("execute", "run", "query"):
        method = getattr(client, name, None)
        if callable(method):
            return method
    raise ValueError("Grafeo client must have execute(), run(), or query() method")


def _is_engine_panic(exc: BaseException) -> bool:
    # pyo3 turns a Rust panic into pyo3_runtime.PanicException, a BaseException
    # subclass that `except Exception` does not catch. grafeo 0.5.44 panics on,
    # for example, a vector search whose query has the wrong number of dimensions.
    cls = type(exc)
    return cls.__name__ == "PanicException" and cls.__module__ == "pyo3_runtime"


def execute_query(
    client: Any,
    query: str,
) -> list[dict[str, Any]]:
    """Execute query against Grafeo.

    Args:
        client: ``grafeo.GrafeoDB`` (or any object with execute(), run() or query())
        query: Grafeo query string (one statement)

    Returns:
        List of points

    Raises:
        RuntimeError: if the engine panics; ``grafeo.GrafeoError`` (a RuntimeError)
            for regular query errors.
    """
    run = _query_method(client)
    try:
        results = run(query)
    except BaseException as exc:
        if not _is_engine_panic(exc):
            raise
        raise RuntimeError(f"Grafeo engine error: {exc}") from exc
    return to_points(results)
