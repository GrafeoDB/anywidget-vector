"""Tests for the embedded Grafeo backend: converter and client."""

from __future__ import annotations

import json
import math
from decimal import Decimal
from typing import Any

import numpy as np
import pytest

from anywidget_vector.backends.grafeo.client import execute_query
from anywidget_vector.backends.grafeo.converter import column_key, is_node, row_to_point, to_points


def _contains_decimal(value: Any) -> bool:
    if isinstance(value, Decimal):
        return True
    if isinstance(value, dict):
        return any(_contains_decimal(v) for v in value.values())
    if isinstance(value, list | tuple):
        return any(_contains_decimal(v) for v in value)
    return False


class TestColumnKey:
    @pytest.mark.parametrize(
        ("column", "key"),
        [
            ("n.embedding", "embedding"),
            ("doc.name", "name"),
            ("id(n)", "id"),
            ("ID( n )", "id"),
            ("name", "name"),
            ("count(n)", "count(n)"),
            ("n.a.b", "n.a.b"),
            ("cosine_similarity(n.embedding, $q)", "cosine_similarity(n.embedding, $q)"),
        ],
    )
    def test_column_key_maps_expression_names(self, column, key):
        assert column_key(column) == key


class TestRowToPoint:
    def test_row_to_point_node_value(self):
        node = {"_id": 7, "_labels": ["Doc"], "name": "a", "embedding": [0.5, 0.25, 0.125, 9.0]}
        point = row_to_point({"n": node, "distance": 0.1}, 0)
        assert point == {
            "id": "7",
            "labels": ["Doc"],
            "name": "a",
            "distance": 0.1,
            "vector": [0.5, 0.25, 0.125, 9.0],
            "x": 0.5,
            "y": 0.25,
            "z": 0.125,
        }

    def test_row_to_point_engine_id_wins_over_property(self):
        point = row_to_point({"n": {"_id": 3, "_labels": [], "id": "user-id"}}, 0)
        assert point["id"] == "3"

    def test_row_to_point_explicit_coordinates_win_over_vector(self):
        point = row_to_point({"embedding": [9.0, 9.0, 9.0], "x": 1, "y": 2, "z": 3}, 0)
        assert (point["x"], point["y"], point["z"]) == (1.0, 2.0, 3.0)
        assert point["vector"] == [9.0, 9.0, 9.0]

    def test_row_to_point_unaliased_columns(self):
        point = row_to_point({"n.name": "a", "n.embedding": [1.0, 2.0], "id(n)": 4}, 0)
        assert point == {"id": "4", "name": "a", "vector": [1.0, 2.0], "x": 1.0, "y": 2.0, "z": 0.0}

    def test_row_to_point_same_property_of_two_variables(self):
        point = row_to_point({"a.name": "first", "b.name": "second"}, 0)
        assert point["name"] == "first"
        assert point["b.name"] == "second"

    def test_row_to_point_numpy_vector(self):
        point = row_to_point({"vector": np.array([1, 2, 3], dtype=np.float32)}, 0)
        assert point["vector"] == [1.0, 2.0, 3.0]
        assert all(type(v) is float for v in point["vector"])

    def test_row_to_point_non_finite_coordinates_become_zero(self):
        point = row_to_point({"embedding": [math.nan, math.inf, 1.0]}, 0)
        assert (point["x"], point["y"], point["z"]) == (0.0, 0.0, 1.0)
        point = row_to_point({"x": "not a number", "y": None}, 0)
        assert (point["x"], point["y"], point["z"]) == (0.0, 0.0, 0.0)

    def test_row_to_point_empty_and_short_vectors(self):
        assert row_to_point({"vector": []}, 0)["x"] == 0.0
        point = row_to_point({"vector": [5.0]}, 1)
        assert (point["id"], point["x"], point["y"], point["z"]) == ("point_1", 5.0, 0.0, 0.0)

    def test_row_to_point_non_numeric_vector_key_is_a_plain_field(self):
        point = row_to_point({"embedding": "pending"}, 0)
        assert point["embedding"] == "pending"
        assert "vector" not in point

    def test_row_to_point_skips_nulls(self):
        assert row_to_point({"name": None, "score": 1}, 0) == {
            "id": "point_0",
            "score": 1,
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
        }

    def test_row_to_point_decimals_become_floats(self):
        # grafeo 0.6: a GQL number with a point is an exact decimal (decimal.Decimal)
        node = {"_id": 1, "_labels": ["Doc"], "weight": Decimal("1.50"), "tags": [Decimal("0.1"), "a"]}
        row = {
            "n": node,
            "score": Decimal("0.25"),
            "meta": {"a": Decimal("3.0"), "b": (Decimal("1"),)},
            "embedding": [Decimal("9.0"), Decimal("8.0"), Decimal("7.0")],
            "x": Decimal("1.5"),
        }
        point = row_to_point(row, 0)
        assert point == {
            "id": "1",
            "labels": ["Doc"],
            "weight": 1.5,
            "tags": [0.1, "a"],
            "score": 0.25,
            "meta": {"a": 3.0, "b": [1.0]},
            "vector": [9.0, 8.0, 7.0],
            "x": 1.5,
            "y": 8.0,
            "z": 7.0,
        }
        assert not _contains_decimal(point)
        json.dumps(point)  # points travel to the browser as JSON

    def test_is_node(self):
        assert is_node({"_id": 1, "_labels": ["A"]})
        assert not is_node({"_id": 1, "_source": 0, "_target": 2, "_type": "REL"})
        assert not is_node({"id": 1})


class TestToPoints:
    def test_to_points_from_iterable_rows(self):
        class FakeResult:
            def __iter__(self):
                return iter([{"n.name": "a", "n.embedding": [1.0, 0.0, 0.0]}])

        assert to_points(FakeResult())[0]["name"] == "a"

    def test_to_points_from_dataframe_like(self):
        class FakeFrame:
            def to_dict(self, orient):
                assert orient == "records"
                return [{"id": 1, "x": 0.5}]

        assert to_points(FakeFrame()) == [{"id": "1", "x": 0.5, "y": 0.0, "z": 0.0}]

    def test_to_points_raw_values(self):
        assert to_points([3]) == [{"id": "point_0", "data": 3, "x": 0.0, "y": 0.0, "z": 0.0}]


class _Builder:
    """Like grafeo's QueryBuilder: not iterable."""


class TestExecuteQuery:
    def test_execute_query_prefers_execute_over_query_builder(self):
        class FakeDB:
            def query(self, q):
                return _Builder()

            def execute(self, q):
                return [{"name": "a", "x": 1}]

        assert execute_query(FakeDB(), "MATCH (n) RETURN n")[0]["name"] == "a"

    def test_execute_query_falls_back_to_run(self):
        class FakeSession:
            def run(self, q):
                return [{"x": 2}]

        assert execute_query(FakeSession(), "q")[0]["x"] == 2.0

    def test_execute_query_without_query_method(self):
        with pytest.raises(ValueError, match="execute"):
            execute_query(object(), "q")

    def test_execute_query_turns_engine_panic_into_runtime_error(self):
        panic = type("PanicException", (BaseException,), {"__module__": "pyo3_runtime"})

        class FakeDB:
            def execute(self, q):
                raise panic("assertion failed: dimensions")

        with pytest.raises(RuntimeError, match="Grafeo engine error: assertion failed"):
            execute_query(FakeDB(), "q")

    def test_execute_query_keeps_other_base_exceptions(self):
        class FakeDB:
            def execute(self, q):
                raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            execute_query(FakeDB(), "q")
