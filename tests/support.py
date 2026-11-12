"""Test data and helpers shared by several test modules."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

# Small 3-D corpus: names, embeddings and a category to filter on.
DOCS: list[tuple[str, list[float], str]] = [
    ("a", [1.0, 0.0, 0.0], "x"),
    ("b", [0.0, 2.0, 0.0], "y"),
    ("c", [0.9, 0.1, 0.0], "x"),
    ("d", [0.0, 0.0, 3.0], "y"),
    ("e", [-1.0, 0.5, 0.25], "x"),
]

# The four metric names the widget offers (distance_metric, compute_distances)
WIDGET_METRICS = ("euclidean", "cosine", "manhattan", "dot_product")

NODE = shutil.which("node")


def _node_strips_types() -> bool:
    """Whether Node runs .ts files without a flag (type stripping: Node 22.18 or later)."""
    if NODE is None:
        return False
    proc = subprocess.run([NODE, "--version"], capture_output=True, text=True, timeout=30, check=False)
    try:
        major, minor = (int(part) for part in proc.stdout.strip().lstrip("v").split(".")[:2])
    except ValueError:
        return False
    return (major, minor) >= (22, 18)


# The tests import the TypeScript sources directly, so they need a Node that strips types
NODE_RUNS_TS = _node_strips_types()


def run_node_module(source: str, tmp_path: Path) -> str:
    """Run JavaScript as an ES module with Node and return stdout (fails the test on error)."""
    assert NODE is not None
    script = tmp_path / "check.mjs"
    script.write_text(source, encoding="utf-8")
    proc = subprocess.run([NODE, str(script)], capture_output=True, text=True, timeout=60, check=False)
    assert proc.returncode == 0, f"node failed:\n{proc.stderr}\n{proc.stdout}"
    return proc.stdout


def run_node_ts_module(source: str, tmp_path: Path) -> str:
    """Run TypeScript as an ES module with Node (type stripping) and return stdout (fails the test on error)."""
    assert NODE is not None
    script = tmp_path / "check.ts"
    script.write_text(source, encoding="utf-8")
    proc = subprocess.run([NODE, str(script)], capture_output=True, text=True, timeout=60, check=False)
    assert proc.returncode == 0, f"node failed:\n{proc.stderr}\n{proc.stdout}"
    return proc.stdout
