"""Tests for VectorSpace widget."""

from anywidget_vector import VectorSpace


class TestVectorSpaceInit:
    """Test VectorSpace initialization."""

    def test_empty_init(self):
        """Test empty initialization."""
        widget = VectorSpace()
        assert widget.points == []
        assert widget.width == 800
        assert widget.height == 600

    def test_with_points(self):
        """Test initialization with points."""
        points = [
            {"id": "a", "x": 0.1, "y": 0.2, "z": 0.3},
            {"id": "b", "x": 0.4, "y": 0.5, "z": 0.6},
        ]
        widget = VectorSpace(points=points)
        assert len(widget.points) == 2
        assert widget.points[0]["id"] == "a"

    def test_custom_dimensions(self):
        """Test custom width and height."""
        widget = VectorSpace(width=1200, height=800)
        assert widget.width == 1200
        assert widget.height == 800


class TestFromDict:
    """Test from_dict factory method."""

    def test_from_dict_with_points_key(self):
        """Test from_dict with points key."""
        data = {
            "points": [
                {"id": "p1", "x": 0, "y": 0, "z": 0},
                {"id": "p2", "x": 1, "y": 1, "z": 1},
            ]
        }
        widget = VectorSpace.from_dict(data)
        assert len(widget.points) == 2

    def test_from_dict_with_list(self):
        """Test from_dict with list input."""
        data = [
            {"id": "p1", "x": 0, "y": 0, "z": 0},
            {"id": "p2", "x": 1, "y": 1, "z": 1},
        ]
        widget = VectorSpace.from_dict(data)
        assert len(widget.points) == 2


class TestFromArrays:
    """Test from_arrays factory method."""

    def test_from_arrays_basic(self):
        """Test from_arrays with positions."""
        positions = [[0, 0, 0], [1, 1, 1], [2, 2, 2]]
        widget = VectorSpace.from_arrays(positions)
        assert len(widget.points) == 3
        assert widget.points[0]["x"] == 0
        assert widget.points[2]["z"] == 2

    def test_from_arrays_with_labels(self):
        """Test from_arrays with labels."""
        positions = [[0, 0, 0], [1, 1, 1]]
        labels = ["First", "Second"]
        widget = VectorSpace.from_arrays(positions, labels=labels)
        assert widget.points[0]["label"] == "First"
        assert widget.points[1]["label"] == "Second"

    def test_from_arrays_2d(self):
        """Test from_arrays with 2D positions."""
        positions = [[0, 1], [2, 3]]
        widget = VectorSpace.from_arrays(positions)
        assert widget.points[0]["z"] == 0  # Default z


class TestDefaults:
    """Test default trait values."""

    def test_default_background(self):
        """Test default background color."""
        widget = VectorSpace()
        assert widget.background == "#1a1a2e"

    def test_default_axes(self):
        """Test default axes settings."""
        widget = VectorSpace()
        assert widget.show_axes is True
        assert widget.show_grid is True

    def test_default_color_scale(self):
        """Test default color scale."""
        widget = VectorSpace()
        assert widget.color_scale == "viridis"

    def test_default_camera(self):
        """Test default camera position."""
        widget = VectorSpace()
        assert widget.camera_position == [2, 2, 2]
        assert widget.camera_target == [0, 0, 0]


class TestSelection:
    """Test selection methods."""

    def test_select(self):
        """Test programmatic selection."""
        widget = VectorSpace(points=[{"id": "a"}, {"id": "b"}])
        widget.select(["a"])
        assert widget.selected_points == ["a"]

    def test_clear_selection(self):
        """Test clearing selection."""
        widget = VectorSpace(points=[{"id": "a"}])
        widget.selected_points = ["a"]
        widget.clear_selection()
        assert widget.selected_points == []


class TestCamera:
    """Test camera control methods."""

    def test_reset_camera(self):
        """Test camera reset."""
        widget = VectorSpace()
        widget.camera_position = [5, 5, 5]
        widget.reset_camera()
        assert widget.camera_position == [2, 2, 2]
        assert widget.camera_target == [0, 0, 0]

    def test_focus_on(self):
        """Test focus on points."""
        widget = VectorSpace(
            points=[
                {"id": "a", "x": 1, "y": 1, "z": 1},
                {"id": "b", "x": 3, "y": 3, "z": 3},
            ]
        )
        widget.focus_on(["a", "b"])
        assert widget.camera_target == [2, 2, 2]  # Centroid


class TestExport:
    """Test export methods."""

    def test_to_json(self):
        """Test JSON export."""
        widget = VectorSpace(points=[{"id": "a", "x": 1, "y": 2, "z": 3}])
        json_str = widget.to_json()
        assert '"id": "a"' in json_str
        assert '"x": 1' in json_str


class TestTraitlets:
    """Test traitlet synchronization."""

    def test_color_field(self):
        """Test color field setting."""
        widget = VectorSpace(color_field="cluster")
        assert widget.color_field == "cluster"

    def test_size_range(self):
        """Test size range setting."""
        widget = VectorSpace(size_range=[0.01, 0.2])
        assert widget.size_range == [0.01, 0.2]

    def test_shape_map(self):
        """Test shape mapping."""
        shape_map = {"type_a": "cube", "type_b": "cone"}
        widget = VectorSpace(shape_map=shape_map)
        assert widget.shape_map == shape_map
