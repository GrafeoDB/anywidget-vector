"""Edge cases for widget.py: non-finite values, ragged or empty vectors,
high dimensions, large point counts and the HTML export."""

from __future__ import annotations

import importlib.metadata
import json
import math
import re
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import anywidget_vector
from anywidget_vector import VectorSpace
from anywidget_vector.demo import DEMO_QUERY, demo_points, demo_vector


def _no_nan_json(text: str) -> object:
    def reject(token: str) -> None:
        raise AssertionError(f"non-standard JSON token {token}")

    return json.loads(text, parse_constant=reject)


def _exported_data(html: str) -> list[dict[str, Any]]:
    match = re.search(r"^const DATA = (.*);$", html, re.MULTILINE)
    assert match
    return json.loads(match.group(1))


class TestNonFiniteValues:
    def test_points_nan_coordinate_replaced_with_none(self):
        with pytest.warns(RuntimeWarning, match="1 non-finite value"):
            widget = VectorSpace(points=[{"id": "a", "x": math.nan, "y": 1.0, "z": 0.0}])
        assert widget.points == [{"id": "a", "x": None, "y": 1.0, "z": 0.0}]

    def test_points_infinity_in_any_field_replaced(self):
        widget = VectorSpace()
        with pytest.warns(RuntimeWarning, match="2 non-finite values?"):
            widget.points = [{"id": "a", "x": 0.0, "score": math.inf}, {"id": "b", "x": -math.inf}]
        assert widget.points[0]["score"] is None
        assert widget.points[1]["x"] is None

    def test_points_finite_values_untouched(self):
        points = [{"id": "a", "x": 1.5, "y": 0, "z": -2.0, "label": "nan"}]
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            widget = VectorSpace(points=points)
        assert widget.points == points

    def test_points_validator_does_not_mutate_input(self):
        original = {"id": "a", "x": math.nan}
        with pytest.warns(RuntimeWarning):
            VectorSpace(points=[original])
        assert math.isnan(original["x"])

    def test_points_nested_vector_values_kept(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            widget = VectorSpace(points=[{"id": "a", "x": 0.0, "vector": [math.nan, 1.0]}])
        assert math.isnan(widget.points[0]["vector"][0])

    def test_from_dataframe_missing_values(self):
        class FakeDF:
            def to_dict(self, orient):
                return [{"x": 0.0, "y": 1.0, "z": math.nan, "weight": math.nan}]

        with pytest.warns(RuntimeWarning, match="2 non-finite"):
            widget = VectorSpace.from_dataframe(FakeDF())
        assert widget.points[0]["z"] is None
        assert widget.points[0]["weight"] is None

    def test_to_json_is_standard_json_after_nan(self):
        with pytest.warns(RuntimeWarning):
            widget = VectorSpace(points=[{"id": "a", "x": math.nan, "y": 0.0, "z": 0.0}])
        assert _no_nan_json(widget.to_json()) == [{"id": "a", "x": None, "y": 0.0, "z": 0.0}]

    def test_distances_and_focus_with_replaced_coordinate(self):
        with pytest.warns(RuntimeWarning):
            widget = VectorSpace(points=[{"id": "a", "x": math.nan, "y": 0.0}, {"id": "b", "x": 1.0, "y": None}])
        # None coordinates count as 0, like in the frontend
        widget.color_by_distance("a")
        assert widget.points[1]["_distance"] == pytest.approx(1.0)
        assert widget.find_neighbors("b") == [("a", pytest.approx(1.0))]
        widget.focus_on(["a", "b"])
        assert widget.camera_target == [0.5, 0.0, 0.0]


class TestVectorFieldDistances:
    def test_compute_distances_skips_missing_and_empty_vectors(self):
        widget = VectorSpace(
            points=[
                {"id": "ref", "emb": [1.0, 0.0]},
                {"id": "ok", "emb": [0.0, 1.0]},
                {"id": "missing"},
                {"id": "empty", "emb": []},
            ]
        )
        assert widget.compute_distances("ref", metric="euclidean", vector_field="emb") == {
            "ok": pytest.approx(math.sqrt(2))
        }

    def test_compute_distances_reference_without_vector(self):
        widget = VectorSpace(points=[{"id": "ref"}, {"id": "b", "emb": [1.0]}])
        assert widget.compute_distances("ref", vector_field="emb") == {}

    def test_compute_distances_ragged_vectors_raise(self):
        widget = VectorSpace(points=[{"id": "ref", "emb": [1.0, 0.0, 0.0]}, {"id": "short", "emb": [1.0, 0.0]}])
        with pytest.raises(ValueError, match=r"3 dimensions.*'short'"):
            widget.compute_distances("ref", vector_field="emb")

    def test_compute_distances_high_dimensional_cosine(self):
        rng = np.random.default_rng(0)
        vecs = rng.normal(size=(3, 1536))
        widget = VectorSpace(points=[{"id": str(i), "emb": v.tolist()} for i, v in enumerate(vecs)])
        distances = widget.compute_distances("0", metric="cosine", vector_field="emb")
        expected = 1 - vecs[1] @ vecs[0] / (np.linalg.norm(vecs[1]) * np.linalg.norm(vecs[0]))
        assert distances["1"] == pytest.approx(expected)

    def test_cosine_zero_vector_is_max_distance(self):
        widget = VectorSpace(points=[{"id": "ref", "emb": [0.0, 0.0]}, {"id": "b", "emb": [1.0, 0.0]}])
        assert widget.compute_distances("ref", metric="cosine", vector_field="emb") == {"b": 1.0}


class TestAddNumpyValidation:
    def test_add_numpy_ragged_rows(self):
        with pytest.raises(ValueError, match="equal-length rows"):
            VectorSpace().add_numpy([[1.0, 2.0, 3.0], [1.0, 2.0]])

    @pytest.mark.parametrize("positions", [[1.0, 2.0, 3.0], [[[1.0, 2.0]]]])
    def test_add_numpy_wrong_rank(self, positions):
        with pytest.raises(ValueError, match="2-D array"):
            VectorSpace().add_numpy(positions)

    def test_add_numpy_single_column(self):
        with pytest.raises(ValueError, match="at least 2 columns"):
            VectorSpace().add_numpy([[1.0], [2.0]])

    def test_add_numpy_ids_length_mismatch(self):
        with pytest.raises(ValueError, match="ids has 1 entries"):
            VectorSpace().add_numpy([[0.0, 0.0], [1.0, 1.0]], ids=["only-one"])

    def test_add_numpy_metadata_length_mismatch(self):
        with pytest.raises(ValueError, match="metadata\\['cluster'\\]"):
            VectorSpace().add_numpy([[0.0, 0.0], [1.0, 1.0]], metadata={"cluster": [1, 2, 3]})

    def test_add_numpy_empty(self):
        widget = VectorSpace().add_numpy(np.zeros((0, 3)))
        assert widget.points == []
        widget = VectorSpace().add_numpy(np.zeros((0, 768)))
        assert widget.points == []

    def test_add_numpy_nan_low_dimensional_becomes_none(self):
        with pytest.warns(RuntimeWarning):
            widget = VectorSpace().add_numpy([[0.0, math.nan, 1.0]])
        assert widget.points[0]["y"] is None


class TestHighDimensional:
    def test_add_numpy_single_high_dim_vector(self):
        widget = VectorSpace().add_numpy(np.ones((1, 768)), ids=["only"])
        assert widget.points == [{"id": "only", "x": 0.0, "y": 0.0, "z": 0.0}]

    def test_add_numpy_two_high_dim_vectors(self):
        widget = VectorSpace().add_numpy(np.eye(2, 768))
        assert len(widget.points) == 2
        assert all(p["z"] == 0.0 for p in widget.points)
        assert widget.points[0]["x"] == pytest.approx(-widget.points[1]["x"])

    def test_add_numpy_high_dim_then_project(self):
        rng = np.random.default_rng(1)
        widget = VectorSpace().add_numpy(rng.normal(size=(50, 768)), labels=[f"p{i}" for i in range(50)])
        assert len(widget.points) == 50
        widget.project("pca")
        for axis in ("x", "y", "z"):
            values = [p[axis] for p in widget.points]
            assert min(values) == pytest.approx(-1.0)
            assert max(values) == pytest.approx(1.0)
        assert widget.points[3]["label"] == "p3"

    def test_add_numpy_high_dim_nan_leaves_state_unchanged(self):
        widget = VectorSpace().add_numpy(np.ones((2, 5)))
        bad = np.ones((1, 5))
        bad[0, 2] = math.nan
        with pytest.raises(ValueError, match="NaN or infinite"):
            widget.add_numpy(bad)
        assert len(widget.points) == 2
        assert widget._vectors.shape == (2, 5)

    def test_project_single_point(self):
        widget = VectorSpace(points=[{"id": "a", "vector": [1.0, 2.0, 3.0, 4.0]}])
        widget.project("pca")
        assert (widget.points[0]["x"], widget.points[0]["y"], widget.points[0]["z"]) == (0.0, 0.0, 0.0)

    def test_project_ragged_point_vectors(self):
        widget = VectorSpace(points=[{"id": "a", "vector": [1.0, 2.0, 3.0, 4.0]}, {"id": "b", "vector": [1.0]}])
        with pytest.raises(ValueError, match="different lengths"):
            widget.project("pca")

    def test_project_without_points(self):
        with pytest.raises(ValueError, match="No vectors available"):
            VectorSpace().project("pca")

    def test_project_non_finite_vectors(self):
        widget = VectorSpace(points=[{"id": "a"}, {"id": "b"}]).set_vectors([[1.0, math.inf, 0.0, 0.0], [0.0] * 4])
        with pytest.raises(ValueError, match="NaN or infinite"):
            widget.project("pca")

    def test_set_vectors_ragged(self):
        with pytest.raises(ValueError, match="equal-length rows"):
            VectorSpace().set_vectors([[1.0, 2.0], [1.0]])

    def test_project_unknown_method(self):
        widget = VectorSpace(points=[{"id": "a", "vector": [1.0, 2.0, 3.0, 4.0]}])
        with pytest.raises(ValueError, match="Unknown projection method"):
            widget.project("isomap")


class TestLargePointCounts:
    def test_hundred_thousand_points(self):
        rng = np.random.default_rng(2)
        widget = VectorSpace().add_numpy(rng.normal(size=(100_000, 3)))
        assert len(widget.points) == 100_000
        assert widget.points[-1]["id"] == "point_99999"
        # The point budget is applied by the frontend; Python keeps every point
        assert widget.point_budget == 100_000
        widget.add_points([{"x": 0.0, "y": 0.0, "z": 0.0}])
        assert len(widget.points) == 100_001

    def test_large_export_round_trips(self):
        rng = np.random.default_rng(3)
        widget = VectorSpace().add_numpy(rng.normal(size=(20_000, 3)))
        html = widget.to_html()
        assert len(_exported_data(html)) == 20_000

    def test_find_neighbors_large(self):
        rng = np.random.default_rng(4)
        widget = VectorSpace().add_numpy(rng.normal(size=(5_000, 3)))
        neighbors = widget.find_neighbors("point_0", k=10)
        assert len(neighbors) == 10
        assert [d for _, d in neighbors] == sorted(d for _, d in neighbors)


class TestHtmlExport:
    def test_to_html_script_breaking_data_is_escaped(self):
        label = "</script><script>alert('x')</script><!--"
        widget = VectorSpace(points=[{"id": "a", "x": 0, "y": 0, "z": 0, "label": label}])
        html = widget.to_html()
        assert html.count("</script>") == 1
        assert "<!--" not in html
        assert _exported_data(html) == [{"id": "a", "x": 0, "y": 0, "z": 0, "label": label}]

    def test_to_html_title_is_escaped(self):
        html = VectorSpace().to_html(title="A & B <i>")
        assert "<title>A &amp; B &lt;i&gt;</title>" in html

    def test_to_html_tooltip_builds_text_nodes(self):
        html = VectorSpace().to_html()
        assert "innerHTML" not in html
        assert "textContent" in html

    def test_to_html_non_finite_values_exported_as_null(self):
        with pytest.warns(RuntimeWarning):
            widget = VectorSpace(points=[{"id": "a", "x": math.inf, "y": 0.0, "z": 0.0}])
        assert _exported_data(widget.to_html()) == [{"id": "a", "x": None, "y": 0.0, "z": 0.0}]

    def test_to_html_options_round_trip(self):
        widget = VectorSpace(color_field="c</script>", axis_labels={"x": "<b>", "y": "Y", "z": "Z"})
        match = re.search(r"^const OPTIONS = (.*);$", widget.to_html(), re.MULTILINE)
        assert match
        options = json.loads(match.group(1))
        assert options["color_field"] == "c</script>"
        assert options["axis_labels"]["x"] == "<b>"

    def test_save_html_utf8(self, tmp_path):
        widget = VectorSpace(points=[{"id": "a", "x": 0, "y": 0, "z": 0, "label": "\U0001f600 \u2028"}])
        path = tmp_path / "out.html"
        widget.save_html(str(path), title="Emoji")
        assert _exported_data(path.read_text(encoding="utf-8"))[0]["label"] == "\U0001f600 \u2028"


class TestPythonQueryHandling:
    def test_execute_query_without_backend_client(self):
        widget = VectorSpace(backend="grafeo")
        widget._execute_query += 1
        assert widget.connection_status == "error"
        assert "set_backend" in str(widget.query_error)

    def test_execute_query_ignored_for_browser_backend(self):
        widget = VectorSpace(backend="qdrant")
        widget._execute_query += 1
        assert widget.connection_status == "disconnected"


class TestPackage:
    def test_version_matches_metadata(self):
        assert anywidget_vector.__version__ == importlib.metadata.version("anywidget-vector")

    def test_demo_vector(self):
        widget = demo_vector()
        assert widget.backend == "grafeo"
        assert widget.grafeo_connection_mode == "wasm"
        assert widget.query_input == DEMO_QUERY
        assert len(widget.points) == 64
        assert len({p["id"] for p in widget.points}) == 64
        assert all(math.isfinite(p[a]) for p in widget.points for a in ("x", "y", "z"))
        assert demo_vector(width=400, color_field="label").width == 400

    def test_demo_points_are_the_silicon_valley_nodes(self):
        points = demo_points()
        categories = {p["category"] for p in points}
        # Eight node labels: one palette colour each, none of them "Other"
        assert categories == {"Person", "Company", "Product", "Technology", "AI", "Place", "City", "Event"}
        assert all(len(p["vector"]) == 384 and p["description"] for p in points)
        assert next(p for p in points if p["id"] == "middle-out")["label"] == "Middle-out compression"
        assert demo_points() == points, "the PCA's axis signs are fixed, so the picture never mirrors"

    def test_demo_keeps_the_real_embeddings(self):
        widget = demo_vector()
        distances = widget.compute_distances("middle-out", metric="cosine", vector_field="vector")
        nearest = sorted((d, i) for i, d in distances.items() if i != "middle-out")[0][1]
        assert nearest == "pied-piper-app"  # "Pied Piper platform", as Grafeo WASM ranks it
        assert widget.project("pca") is widget  # the stored vectors feed project()

    def test_demo_statements_place_every_browser_node_where_its_point_is(self):
        widget = demo_vector()
        statements = json.loads(widget._demo_data)
        assert widget._demo_mode is True
        assert len(statements) == 64
        anton = next(p for p in widget.points if p["id"] == "anton")
        assert statements[0] == (
            f"MATCH (n:AI {{key: 'anton'}}) SET n.x = {anton['x']:.6e}, n.y = {anton['y']:.6e}, "
            f"n.z = {anton['z']:.6e}, n.category = 'AI'"
        )

    def test_demo_query_is_the_one_the_wasm_smoke_test_runs(self):
        smoke = (Path(__file__).parent / "js" / "wasm_smoke.ts").read_text(encoding="utf-8")
        match_part, return_part = DEMO_QUERY.split("RETURN ")
        assert f'"{match_part}"' in smoke
        assert f'"RETURN {return_part}"' in smoke

    def test_demo_with_points_of_its_own_keeps_them(self):
        widget = demo_vector(points=[{"id": "a", "x": 0, "y": 0, "z": 0}])
        assert [p["id"] for p in widget.points] == ["a"]
