"""Demo module for anywidget-vector.

Creates a pre-populated vector space widget with emoji embeddings.
Renders immediately without any backend setup — just filter and explore.

Usage:
    uv add "anywidget-vector[demo]"

    from anywidget_vector.demo import demo_vector
    vs = demo_vector()
"""

from __future__ import annotations

from typing import Any

from anywidget_vector.widget import VectorSpace

# Emoji embeddings in 3D space, grouped into semantic clusters.
# Coordinates place similar emojis near each other, forming
# visually distinct clusters when colored by category.
DEMO_POINTS: list[dict[str, Any]] = [
    # Faces cluster (centered around x=2.5, y=0, z=0)
    {"id": "grinning", "label": "\U0001f600 grinning", "category": "faces", "x": 2.6, "y": 0.2, "z": 0.1},
    {"id": "laughing", "label": "\U0001f602 tears of joy", "category": "faces", "x": 2.8, "y": -0.1, "z": -0.1},
    {"id": "heart_eyes", "label": "\U0001f60d heart eyes", "category": "faces", "x": 2.3, "y": 0.4, "z": 0.3},
    {"id": "thinking", "label": "\U0001f914 thinking", "category": "faces", "x": 2.4, "y": -0.3, "z": -0.2},
    {"id": "sunglasses", "label": "\U0001f60e sunglasses", "category": "faces", "x": 2.7, "y": 0.1, "z": -0.3},
    {"id": "wink", "label": "\U0001f609 wink", "category": "faces", "x": 2.5, "y": 0.3, "z": 0.2},
    {"id": "sleeping", "label": "\U0001f634 sleeping", "category": "faces", "x": 2.2, "y": -0.4, "z": 0.4},
    {"id": "mind_blown", "label": "\U0001f92f mind blown", "category": "faces", "x": 2.9, "y": 0.0, "z": -0.4},
    {"id": "nerd", "label": "\U0001f913 nerd", "category": "faces", "x": 2.4, "y": -0.2, "z": 0.0},
    # Animals cluster (centered around x=-2, y=2, z=0)
    {"id": "cat", "label": "\U0001f431 cat", "category": "animals", "x": -1.9, "y": 2.2, "z": 0.1},
    {"id": "dog", "label": "\U0001f436 dog", "category": "animals", "x": -2.2, "y": 1.8, "z": -0.2},
    {"id": "unicorn", "label": "\U0001f984 unicorn", "category": "animals", "x": -1.7, "y": 2.5, "z": 0.4},
    {"id": "butterfly", "label": "\U0001f98b butterfly", "category": "animals", "x": -2.3, "y": 2.1, "z": 0.3},
    {"id": "dolphin", "label": "\U0001f42c dolphin", "category": "animals", "x": -1.8, "y": 2.4, "z": -0.3},
    {"id": "owl", "label": "\U0001f989 owl", "category": "animals", "x": -2.1, "y": 1.9, "z": 0.2},
    {"id": "penguin", "label": "\U0001f427 penguin", "category": "animals", "x": -2.4, "y": 2.3, "z": -0.1},
    {"id": "octopus", "label": "\U0001f419 octopus", "category": "animals", "x": -1.6, "y": 2.0, "z": -0.4},
    {"id": "fox", "label": "\U0001f98a fox", "category": "animals", "x": -2.0, "y": 2.6, "z": 0.0},
    # Food cluster (centered around x=-2, y=-2, z=0)
    {"id": "pizza", "label": "\U0001f355 pizza", "category": "food", "x": -2.1, "y": -1.8, "z": 0.2},
    {"id": "sushi", "label": "\U0001f363 sushi", "category": "food", "x": -1.8, "y": -2.2, "z": -0.1},
    {"id": "taco", "label": "\U0001f32e taco", "category": "food", "x": -2.3, "y": -1.9, "z": 0.3},
    {"id": "ramen", "label": "\U0001f35c ramen", "category": "food", "x": -1.9, "y": -2.4, "z": -0.2},
    {"id": "ice_cream", "label": "\U0001f366 ice cream", "category": "food", "x": -2.2, "y": -2.1, "z": 0.4},
    {"id": "avocado", "label": "\U0001f951 avocado", "category": "food", "x": -1.7, "y": -1.7, "z": -0.3},
    {"id": "cake", "label": "\U0001f370 cake", "category": "food", "x": -2.4, "y": -2.3, "z": 0.1},
    {"id": "coffee", "label": "\u2615 coffee", "category": "food", "x": -2.0, "y": -2.0, "z": -0.4},
    # Nature cluster (centered around x=0, y=0, z=2.5)
    {"id": "sun", "label": "\u2600\ufe0f sun", "category": "nature", "x": 0.2, "y": 0.1, "z": 2.6},
    {"id": "rainbow", "label": "\U0001f308 rainbow", "category": "nature", "x": -0.1, "y": 0.3, "z": 2.8},
    {"id": "snowflake", "label": "\u2744\ufe0f snowflake", "category": "nature", "x": 0.3, "y": -0.2, "z": 2.3},
    {"id": "fire", "label": "\U0001f525 fire", "category": "nature", "x": -0.2, "y": 0.4, "z": 2.5},
    {"id": "lightning", "label": "\u26a1 lightning", "category": "nature", "x": 0.4, "y": -0.1, "z": 2.7},
    {"id": "ocean", "label": "\U0001f30a ocean wave", "category": "nature", "x": -0.3, "y": -0.3, "z": 2.4},
    {"id": "tree", "label": "\U0001f333 tree", "category": "nature", "x": 0.1, "y": 0.2, "z": 2.2},
    {"id": "star", "label": "\u2b50 star", "category": "nature", "x": 0.0, "y": -0.4, "z": 2.9},
    # Travel cluster (centered around x=0, y=0, z=-2.5)
    {"id": "rocket", "label": "\U0001f680 rocket", "category": "travel", "x": 0.2, "y": 0.1, "z": -2.6},
    {"id": "airplane", "label": "\u2708\ufe0f airplane", "category": "travel", "x": -0.1, "y": 0.3, "z": -2.3},
    {"id": "ship", "label": "\U0001f6a2 ship", "category": "travel", "x": 0.3, "y": -0.2, "z": -2.8},
    {"id": "car", "label": "\U0001f697 car", "category": "travel", "x": -0.2, "y": -0.1, "z": -2.4},
    {"id": "bike", "label": "\U0001f6b2 bicycle", "category": "travel", "x": 0.4, "y": 0.2, "z": -2.5},
    {"id": "train", "label": "\U0001f682 train", "category": "travel", "x": -0.3, "y": 0.4, "z": -2.7},
    {"id": "globe", "label": "\U0001f30d globe", "category": "travel", "x": 0.1, "y": -0.3, "z": -2.2},
    # Sports cluster (centered around x=2, y=-2, z=0)
    {"id": "soccer", "label": "\u26bd soccer", "category": "sports", "x": 2.1, "y": -1.8, "z": 0.2},
    {"id": "basketball", "label": "\U0001f3c0 basketball", "category": "sports", "x": 2.3, "y": -2.2, "z": -0.1},
    {"id": "tennis", "label": "\U0001f3be tennis", "category": "sports", "x": 1.9, "y": -2.1, "z": 0.3},
    {"id": "surfing", "label": "\U0001f3c4 surfing", "category": "sports", "x": 2.4, "y": -1.9, "z": -0.3},
    {"id": "skiing", "label": "\u26f7\ufe0f skiing", "category": "sports", "x": 1.8, "y": -2.4, "z": 0.1},
    {"id": "medal", "label": "\U0001f3c5 medal", "category": "sports", "x": 2.2, "y": -2.0, "z": -0.2},
    {"id": "trophy", "label": "\U0001f3c6 trophy", "category": "sports", "x": 2.0, "y": -2.3, "z": 0.4},
    # Music cluster (centered around x=0, y=2.5, z=0)
    {"id": "guitar", "label": "\U0001f3b8 guitar", "category": "music", "x": 0.2, "y": 2.6, "z": 0.1},
    {"id": "microphone", "label": "\U0001f3a4 microphone", "category": "music", "x": -0.1, "y": 2.3, "z": -0.2},
    {"id": "drums", "label": "\U0001f941 drum", "category": "music", "x": 0.3, "y": 2.8, "z": 0.3},
    {"id": "headphones", "label": "\U0001f3a7 headphones", "category": "music", "x": -0.2, "y": 2.5, "z": -0.1},
    {"id": "notes", "label": "\U0001f3b5 music notes", "category": "music", "x": 0.1, "y": 2.4, "z": 0.2},
    {"id": "saxophone", "label": "\U0001f3b7 saxophone", "category": "music", "x": -0.3, "y": 2.7, "z": -0.3},
    {"id": "violin", "label": "\U0001f3bb violin", "category": "music", "x": 0.4, "y": 2.2, "z": 0.0},
]


def demo_vector(**kwargs: Any) -> VectorSpace:
    """Create a demo VectorSpace widget with emoji embeddings.

    60+ emojis in 7 categories (faces, animals, food, nature, travel,
    sports, music) arranged as clusters in 3D space. Type in the
    filter bar to highlight matching emojis.

    Parameters
    ----------
    **kwargs
        Additional keyword arguments passed to VectorSpace constructor.
        Overrides demo defaults.

    Returns
    -------
    VectorSpace
        A ready-to-use VectorSpace widget with demo data rendered.

    Example
    -------
    >>> from anywidget_vector.demo import demo_vector
    >>> vs = demo_vector()
    >>> vs  # renders in notebook
    """
    defaults: dict[str, Any] = {
        "points": DEMO_POINTS,
        "width": kwargs.pop("width", 900),
        "height": kwargs.pop("height", 600),
        "backend": "grafeo",
        "color_field": "category",
        "show_tooltip": True,
        "tooltip_fields": ["label", "category", "x", "y", "z"],
    }
    defaults.update(kwargs)

    return VectorSpace(**defaults)
