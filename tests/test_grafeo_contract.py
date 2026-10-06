"""Contract tests against the real Grafeo engine (embedded Python backend).

These pin down the engine behavior the widget relies on: how query results
look, the distance metrics and their values, result ordering, ties, filters,
dimension checks and quantization options. When an engine release changes one
of them, a test here fails with a message that names the contract.

Error codes (for example GRAFEO-X001) are never matched: they may change in 0.6.
"""

from __future__ import annotations

import math
from typing import Any

import grafeo
import pytest

from anywidget_vector import VectorSpace
from anywidget_vector.backends.grafeo.client import execute_query
from tests.support import DOCS, WIDGET_METRICS

SEARCH_QUERY = (
    "CALL grafeo.search.vector('Doc', 'embedding', {vector}, {k}) YIELD node_id, distance "
    "NEXT MATCH (n:Doc) WHERE id(n) = node_id RETURN n, distance ORDER BY distance"
)


def _names(db: Any) -> dict[int, str]:
    return {row["id"]: row["name"] for row in db.execute("MATCH (n:Doc) RETURN id(n) AS id, n.name AS name")}


def _widget_for(db: Any) -> VectorSpace:
    """Widget whose points are the :Doc nodes, read through the widget's own Grafeo backend."""
    return VectorSpace(points=execute_query(db, "MATCH (n:Doc) RETURN n"))


def _run_widget_query(widget: VectorSpace, query: str) -> None:
    """Do what the toolbar's Run button does for a Python-side backend."""
    widget.query_input = query
    widget._execute_query += 1


class TestEngineBuild:
    def test_features_include_vector_index(self):
        assert "vector-index" in grafeo.features(), "this grafeo build has no vector index support"

    def test_build_info_matches_version(self):
        info = grafeo.build_info()
        assert info["version"] == grafeo.__version__
        assert "vector-index" in info["features"]


class TestResultShape:
    def test_execute_rows_are_dicts_with_node_maps(self, grafeo_db):
        rows = list(grafeo_db.execute("MATCH (n:Doc) WHERE n.name = 'a' RETURN n"))
        assert len(rows) == 1
        node = rows[0]["n"]
        assert isinstance(node["_id"], int)
        assert node["_labels"] == ["Doc"]
        assert node["name"] == "a"
        assert node["cat"] == "x"
        assert node["embedding"] == [1.0, 0.0, 0.0]
        assert all(isinstance(v, float) for v in node["embedding"])

    def test_unaliased_columns_are_named_after_the_expression(self, grafeo_db):
        result = grafeo_db.execute("MATCH (n:Doc) WHERE n.name = 'a' RETURN n.name, n.embedding, id(n)")
        assert result.columns == ["n.name", "n.embedding", "id(n)"]

    def test_query_builder_is_not_a_result(self, grafeo_db):
        # GrafeoDB.query() returns a QueryBuilder: the widget must call execute()
        assert not isinstance(grafeo_db.query("MATCH (n) RETURN n"), list)
        assert type(grafeo_db.query("MATCH (n) RETURN n")).__name__ == "QueryBuilder"

    def test_execute_query_node_to_point(self, grafeo_db):
        points = execute_query(grafeo_db, "MATCH (n:Doc) WHERE n.name = 'c' RETURN n")
        node_id = next(iter(grafeo_db.execute("MATCH (n:Doc) WHERE n.name = 'c' RETURN id(n) AS id")))["id"]
        assert len(points) == 1
        point = points[0]
        assert point["id"] == str(node_id)
        assert point["labels"] == ["Doc"]
        assert point["name"] == "c"
        assert point["cat"] == "x"
        assert point["vector"] == pytest.approx([0.9, 0.1, 0.0])
        assert (point["x"], point["y"], point["z"]) == pytest.approx((0.9, 0.1, 0.0))

    def test_execute_query_unaliased_columns_to_point(self, grafeo_db):
        points = execute_query(grafeo_db, "MATCH (n:Doc) WHERE n.name = 'b' RETURN n.name, n.embedding, id(n)")
        assert points[0]["name"] == "b"
        assert points[0]["vector"] == [0.0, 2.0, 0.0]
        assert points[0]["y"] == 2.0
        assert points[0]["id"].isdigit()

    def test_query_nan_value_becomes_none_in_widget(self, grafeo_db):
        widget = VectorSpace()
        widget.set_backend("grafeo", client=grafeo_db)
        with pytest.warns(RuntimeWarning, match="non-finite"):
            _run_widget_query(widget, "MATCH (n:Doc) WHERE n.name = 'a' RETURN n.name AS label, 0.0/0.0 AS score")
        assert widget.points[0]["label"] == "a"
        assert widget.points[0]["score"] is None


class TestMetrics:
    @pytest.mark.parametrize("metric", WIDGET_METRICS)
    def test_engine_distance_matches_widget(self, grafeo_db, metric):
        """The widget's compute_distances() agrees with a Grafeo index using the same metric name."""
        grafeo_db.create_vector_index("Doc", "embedding", dimensions=3, metric=metric)
        names = _names(grafeo_db)
        engine = {names[i]: d for i, d in grafeo_db.vector_search("Doc", "embedding", DOCS[0][1], k=len(DOCS))}

        widget = _widget_for(grafeo_db)
        ref_id = next(p["id"] for p in widget.points if p["name"] == "a")
        by_id = {p["id"]: p["name"] for p in widget.points}
        local = {
            by_id[pid]: d for pid, d in widget.compute_distances(ref_id, metric=metric, vector_field="vector").items()
        }

        assert set(engine) == {name for name, _, _ in DOCS}
        assert set(local) == set(engine) - {"a"}
        for name, distance in local.items():
            assert engine[name] == pytest.approx(distance, rel=1e-5, abs=1e-6), (metric, name)
        # The query vector is a's own embedding: a is the closest result
        self_distance = -1.0 if metric == "dot_product" else 0.0
        assert engine["a"] == pytest.approx(self_distance, abs=1e-6)
        assert engine["a"] == min(engine.values())

    def test_unknown_metric_is_rejected(self):
        with pytest.raises(RuntimeError):
            grafeo.GrafeoDB().create_vector_index("Doc", "embedding", dimensions=3, metric="hamming")

    @pytest.mark.parametrize("metric", WIDGET_METRICS)
    def test_results_sorted_by_distance(self, grafeo_db, metric):
        grafeo_db.create_vector_index("Doc", "embedding", dimensions=3, metric=metric)
        results = grafeo_db.vector_search("Doc", "embedding", [0.5, 0.5, 0.5], k=len(DOCS))
        distances = [d for _, d in results]
        assert len(results) == len(DOCS)
        assert distances == sorted(distances)
        assert all(isinstance(i, int) and isinstance(d, float) for i, d in results)

    def test_k_limits_results(self, grafeo_db):
        grafeo_db.create_vector_index("Doc", "embedding", dimensions=3, metric="cosine")
        assert len(grafeo_db.vector_search("Doc", "embedding", [1.0, 0.0, 0.0], k=2)) == 2


class TestTies:
    def test_ties_all_returned_order_unspecified(self):
        db = grafeo.GrafeoDB()
        ids = {db.create_node(["P"], {"v": v}).id: name for name, v in [("t1", [1.0, 0.0]), ("t2", [1.0, 0.0])]}
        ids[db.create_node(["P"], {"v": [0.0, 1.0]}).id] = "far"
        db.create_vector_index("P", "v", dimensions=2, metric="euclidean")

        results = db.vector_search("P", "v", [1.0, 0.0], k=2)
        # Both tied nodes come back; the engine does not promise an order among them
        assert {ids[i] for i, _ in results} == {"t1", "t2"}
        assert [d for _, d in results] == [0.0, 0.0]

    def test_widget_neighbor_ties_keep_point_order(self):
        widget = VectorSpace(
            points=[
                {"id": "ref", "x": 0, "y": 0, "z": 0},
                {"id": "t2", "x": 1, "y": 0, "z": 0},
                {"id": "t1", "x": 0, "y": 1, "z": 0},
            ]
        )
        assert [pid for pid, _ in widget.find_neighbors("ref")] == ["t2", "t1"]


class TestFilters:
    def test_vector_search_filters_on_property(self, grafeo_db):
        grafeo_db.create_vector_index("Doc", "embedding", dimensions=3, metric="cosine")
        names = _names(grafeo_db)
        results = grafeo_db.vector_search("Doc", "embedding", [1.0, 0.0, 0.0], k=5, filters={"cat": "y"})
        assert [names[i] for i, _ in results] == ["b", "d"]

    def test_filter_in_query_reaches_widget(self, grafeo_db):
        points = execute_query(grafeo_db, "MATCH (n:Doc) WHERE n.cat = 'y' RETURN n ORDER BY n.name")
        assert [p["name"] for p in points] == ["b", "d"]


class TestSearchProcedure:
    def test_procedure_columns_and_values(self, grafeo_db):
        grafeo_db.create_vector_index("Doc", "embedding", dimensions=3, metric="cosine")
        result = grafeo_db.execute(
            "CALL grafeo.search.vector('Doc', 'embedding', [1.0, 0.0, 0.0], 3) YIELD node_id, distance "
            "RETURN node_id, distance"
        )
        assert result.columns == ["node_id", "distance"]
        rows = [(r["node_id"], r["distance"]) for r in result]
        direct = grafeo_db.vector_search("Doc", "embedding", [1.0, 0.0, 0.0], k=3)
        assert [i for i, _ in rows] == [i for i, _ in direct]
        assert [d for _, d in rows] == pytest.approx([d for _, d in direct])

    def test_search_query_gives_ordered_points(self, grafeo_db):
        """The k-NN query documented in the README, end to end through the widget."""
        grafeo_db.create_vector_index("Doc", "embedding", dimensions=3, metric="cosine")
        widget = VectorSpace()
        widget.set_backend("grafeo", client=grafeo_db)
        _run_widget_query(widget, SEARCH_QUERY.format(vector="[1.0, 0.0, 0.0]", k=4))

        assert widget.query_error is None
        assert widget.connection_status == "connected"
        names = [p["name"] for p in widget.points]
        assert names[:2] == ["a", "c"]
        assert set(names[2:]) == {"b", "d"}  # tied at cosine distance 1.0
        distances = [p["distance"] for p in widget.points]
        assert distances == sorted(distances)
        assert widget.points[1]["vector"] == pytest.approx([0.9, 0.1, 0.0])
        assert widget.points[1]["x"] == pytest.approx(0.9)

    def test_vector_literal_and_similarity_function(self, grafeo_db):
        points = execute_query(
            grafeo_db,
            "MATCH (n:Doc) RETURN n, cosine_similarity(n.embedding, vector([1.0, 0.0, 0.0])) AS score "
            "ORDER BY score DESC LIMIT 2",
        )
        assert [p["name"] for p in points] == ["a", "c"]
        assert points[0]["score"] == pytest.approx(1.0, abs=1e-6)


class TestDimensions:
    def test_index_infers_dimensions(self, grafeo_db):
        grafeo_db.create_vector_index("Doc", "embedding", metric="euclidean")
        assert len(grafeo_db.vector_search("Doc", "embedding", [1.0, 0.0, 0.0], k=1)) == 1

    def test_wrong_dimension_insert_raises_grafeo_error(self, grafeo_db):
        grafeo_db.create_vector_index("Doc", "embedding", dimensions=3, metric="cosine")
        with pytest.raises(grafeo.GrafeoError):
            grafeo_db.create_node(["Doc"], {"name": "bad", "embedding": [1.0, 0.0]})

    def test_wrong_dimension_search_is_a_query_error_in_widget(self, grafeo_db):
        # grafeo 0.5.44 panics here (pyo3 PanicException, a BaseException); the widget
        # must still report it as a query error instead of letting it escape the callback.
        grafeo_db.create_vector_index("Doc", "embedding", dimensions=3, metric="cosine")
        widget = VectorSpace(points=[{"id": "keep", "x": 0, "y": 0, "z": 0}])
        widget.set_backend("grafeo", client=grafeo_db)
        _run_widget_query(widget, SEARCH_QUERY.format(vector="[1.0, 0.0]", k=2))

        assert widget.connection_status == "error"
        assert widget.query_error
        assert widget.points == [{"id": "keep", "x": 0, "y": 0, "z": 0}]
        # The database is still usable afterwards
        assert len(execute_query(grafeo_db, "MATCH (n:Doc) RETURN n")) == len(DOCS)


class TestQuantization:
    @pytest.mark.parametrize("quantization", [None, "scalar", "binary", "product"])
    def test_quantization_option_accepted(self, grafeo_db, quantization):
        grafeo_db.create_vector_index("Doc", "embedding", dimensions=3, metric="cosine", quantization=quantization)
        names = _names(grafeo_db)
        results = grafeo_db.vector_search("Doc", "embedding", [1.0, 0.0, 0.0], k=3)
        assert names[results[0][0]] == "a"
        assert math.isclose(results[0][1], 0.0, abs_tol=1e-5)


class TestWidgetQueries:
    def test_several_statements_are_a_query_error(self, grafeo_db):
        with pytest.raises(grafeo.GrafeoError):
            execute_query(grafeo_db, "MATCH (n:Doc) RETURN n; MATCH (m:Doc) RETURN m")

        widget = VectorSpace()
        widget.set_backend("grafeo", client=grafeo_db)
        _run_widget_query(widget, "MATCH (n:Doc) RETURN n; MATCH (m:Doc) RETURN m")
        assert widget.connection_status == "error"
        assert widget.query_error

    def test_error_then_success_clears_error(self, grafeo_db):
        widget = VectorSpace()
        widget.set_backend("grafeo", client=grafeo_db)
        _run_widget_query(widget, "MATCH (n:Doc RETURN n")
        assert widget.connection_status == "error"
        _run_widget_query(widget, "MATCH (n:Doc) RETURN n")
        assert widget.query_error is None
        assert widget.connection_status == "connected"
        assert len(widget.points) == len(DOCS)

    def test_empty_result_clears_points_and_connects(self, grafeo_db):
        widget = VectorSpace(points=[{"id": "old", "x": 0, "y": 0, "z": 0}])
        widget.set_backend("grafeo", client=grafeo_db)
        _run_widget_query(widget, "MATCH (n:Doc) WHERE n.name = 'nobody' RETURN n")
        assert widget.points == []
        assert widget.connection_status == "connected"
        assert widget.query_error is None
