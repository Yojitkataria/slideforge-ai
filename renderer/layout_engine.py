"""Grid-based layout engine with strict PPT rules."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


MAX_BULLETS_PER_SLIDE = 5
SLIDE_WIDTH = 10.0
DEFAULT_SPACING = 0.25
DEFAULT_MARGIN = 0.5


BASE_LAYOUT: dict[str, Any] = {
    "margins": {
        "left": DEFAULT_MARGIN,
        "right": DEFAULT_MARGIN,
        "top": 0.5,
        "bottom": 0.5,
    },
    "hierarchy": {
        "require_title": True,
        "allow_subtitle": True,
        "require_body": True,
    },
    "title": {
        "top": 0.5,
        "left": DEFAULT_MARGIN,
        "width": SLIDE_WIDTH - (DEFAULT_MARGIN * 2),
        "font_size": 32,
        "align": "center",
    },
    "content": {
        "top": 1.5,
        "left": DEFAULT_MARGIN,
        "width": SLIDE_WIDTH - (DEFAULT_MARGIN * 2),
        "font_size": 18,
        "spacing": DEFAULT_SPACING,
        "max_bullets": MAX_BULLETS_PER_SLIDE,
        "align": "left",
    },
    "rules": {
        "fixed_margins": True,
        "consistent_spacing": True,
        "enforce_hierarchy": True,
        "no_floating_objects": True,
    },
}


LAYOUT_BY_SLIDE_TYPE: dict[str, dict[str, Any]] = {
    "title": {
        "title": {"top": 1.2, "font_size": 42, "align": "center"},
        "content": {"top": 3.0, "font_size": 22, "align": "center"},
        "hierarchy": {"require_body": False},
    },
    "agenda": {
        "title": {"top": 0.5, "font_size": 34, "align": "center"},
        "content": {"top": 1.6, "font_size": 20, "spacing": 0.3},
    },
    "summary": {
        "title": {"top": 0.5, "font_size": 34, "align": "center"},
        "content": {"top": 1.6, "font_size": 20, "spacing": 0.3},
    },
    "content": {
        "title": {"top": 0.5, "font_size": 32, "align": "center"},
        "content": {"top": 1.6, "font_size": 20, "spacing": 0.3},
    },
    "chart": {
        "title": {"top": 0.4, "font_size": 30, "align": "center"},
        "content": {"top": 1.35, "font_size": 16, "spacing": 0.25},
        "chart_area": {"left": 0.8, "top": 1.5, "width": 8.4, "height": 4.8},
    },
    "table": {
        "title": {"top": 0.4, "font_size": 30, "align": "center"},
        "content": {"top": 1.35, "font_size": 16, "spacing": 0.25},
        "table_area": {"left": 0.6, "top": 1.5, "width": 8.8, "height": 4.8},
    },
    "conclusion": {
        "title": {"top": 0.6, "font_size": 34, "align": "center"},
        "content": {"top": 1.8, "font_size": 20, "spacing": 0.3},
    },
}


def get_layout(slide_type: str) -> dict[str, Any]:
    """
    Return strict layout configuration for the given slide type.

    The returned dict includes the requested structure:
    {
      "title": {"top", "left", "width", "font_size"},
      "content": {"top", "left", "width", "font_size", "spacing"}
    }
    """
    normalized_type = str(slide_type or "content").strip().lower()
    layout = deepcopy(BASE_LAYOUT)
    override = LAYOUT_BY_SLIDE_TYPE.get(normalized_type, LAYOUT_BY_SLIDE_TYPE["content"])
    _deep_merge(layout, override)
    layout["slide_type"] = normalized_type

    # Backward-compatible aliases used by the renderer.
    layout["grid"] = {
        "left_margin": layout["margins"]["left"],
        "right_margin": layout["margins"]["right"],
        "top_margin": layout["margins"]["top"],
        "bottom_margin": layout["margins"]["bottom"],
        "spacing": layout["content"]["spacing"],
    }
    layout["positions"] = {
        "title_top": layout["title"]["top"],
        "subtitle_top": layout["title"]["top"] + 0.55,
        "content_top": layout["content"]["top"],
    }
    layout["fonts"] = {
        "title_size": layout["title"]["font_size"],
        "subtitle_size": max(14, layout["content"]["font_size"]),
        "body_size": layout["content"]["font_size"],
        "caption_size": 14,
    }
    layout["alignment"] = {
        "title": layout["title"].get("align", "center"),
        "subtitle": "left",
        "body": layout["content"].get("align", "left"),
    }
    layout["rules"]["max_bullets_per_slide"] = layout["content"]["max_bullets"]
    layout["rules"]["split_long_content"] = True

    return layout


def split_content(content: list[str], max_bullets: int = MAX_BULLETS_PER_SLIDE) -> list[list[str]]:
    """Split long content into chunks with max_bullets per slide."""
    cleaned = [str(item).strip() for item in content if str(item).strip()]
    max_items = max_bullets if max_bullets > 0 else MAX_BULLETS_PER_SLIDE
    if not cleaned:
        return []
    return [cleaned[i : i + max_items] for i in range(0, len(cleaned), max_items)]


def _deep_merge(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value
