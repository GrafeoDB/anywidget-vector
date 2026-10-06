"""Interactive 3D vector visualization for Python notebooks."""

from importlib.metadata import PackageNotFoundError, version

from anywidget_vector.widget import VectorSpace

__all__ = ["VectorSpace"]

# Single source of truth: the version in pyproject.toml
try:
    __version__ = version("anywidget-vector")
except PackageNotFoundError:  # running from a source tree that is not installed
    __version__ = "0+unknown"
