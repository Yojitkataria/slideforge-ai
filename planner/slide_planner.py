"""Rule-based slide planner for SlideForge AI."""

from __future__ import annotations

import re
from typing import Any


MAX_BULLETS_PER_SLIDE = 5
MIN_SLIDES = 10
MAX_SLIDES = 15
MAX_CHART_POINTS = 8
MAX_TABLE_ROWS = 10
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
NUMBERED_STEP_RE = re.compile(r"^\s*\d+[.)]\s+")

NUMERIC_TOKEN_RE = re.compile(
    r"^\s*([$€£₹])?\s*([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(%|k|m|b)?\s*$",
    re.IGNORECASE,
)


def generate_slide_plan(parsed_markdown: dict[str, Any]) -> dict[str, Any]:
    """Generate a 10-15 slide plan from parsed markdown JSON."""
    title = _safe_text(parsed_markdown.get("title")) or "Untitled Presentation"
    sections = _normalize_sections(parsed_markdown.get("sections", []))

    target_slide_count = _determine_target_slide_count(sections)

    slides: list[dict[str, Any]] = []
    slides.append({"type": "title", "title": title, "content": []})

    if sections:
        slides.append(
            {
                "type": "agenda",
                "title": "Agenda",
                "content": [section["heading"] for section in sections][:MAX_BULLETS_PER_SLIDE],
            }
        )

    slides.append(
        {
            "type": "summary",
            "title": "Executive Summary",
            "content": _build_executive_summary(sections),
        }
    )

    mandatory_content_slides: list[dict[str, Any]] = []
    optional_slides: list[dict[str, Any]] = []

    for section in sections:
        section_content_chunks = _chunk_list(section["content"], MAX_BULLETS_PER_SLIDE)
        infographic_type = _detect_infographic_type(section)

        if section_content_chunks:
            mandatory_content_slides.append(
                {
                    "type": "content",
                    "title": section["heading"],
                    "content": section_content_chunks[0],
                }
            )
            for idx, chunk in enumerate(section_content_chunks[1:], start=2):
                optional_slides.append(
                    {
                        "type": "content",
                        "title": f"{section['heading']} (Part {idx})",
                        "content": chunk,
                    }
                )
        elif section["numbers"]:
            # Keep section represented even if content list is empty.
            mandatory_content_slides.append(
                {
                    "type": "content",
                    "title": section["heading"],
                    "content": [f"Key numeric signals identified: {', '.join(section['numbers'][:5])}"],
                }
            )
        elif section["table"]:
            mandatory_content_slides.append(
                {
                    "type": "content",
                    "title": section["heading"],
                    "content": ["Data table available for this section."],
                }
            )

        chart_data = _build_chart_data(section["numbers"])
        if chart_data:
            optional_slides.append(
                {
                    "type": "chart",
                    "title": f"{section['heading']} - Data Highlights",
                    "data": chart_data,
                }
            )

        if section["table"]:
            optional_slides.append(
                {
                    "type": "table",
                    "title": f"{section['heading']} - Table",
                    "table": section["table"][:MAX_TABLE_ROWS],
                }
            )

        if infographic_type:
            optional_slides.append(
                {
                    "type": infographic_type,
                    "title": f"{section['heading']} - Visual",
                    "content": section["content"][:6],
                }
            )

    slides.extend(mandatory_content_slides)

    # Fill with optional slides until target is reached (reserve one for conclusion).
    for slide in optional_slides:
        if len(slides) + 1 >= target_slide_count:
            break
        slides.append(slide)

    # Ensure minimum slide count before conclusion.
    while len(slides) + 1 < MIN_SLIDES:
        filler = _make_filler_slide(sections, len(slides))
        slides.append(filler)

    slides.append(
        {
            "type": "conclusion",
            "title": "Key Takeaways",
            "content": _build_conclusion_points(sections),
        }
    )

    # Hard cap at MAX_SLIDES: trim optional slides while preserving first 3 and final conclusion.
    if len(slides) > MAX_SLIDES:
        slides = _trim_to_max(slides, MAX_SLIDES)

    return {"slides": slides}


def _normalize_sections(raw_sections: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for idx, raw in enumerate(raw_sections, start=1):
        if not isinstance(raw, dict):
            continue

        heading = _safe_text(raw.get("heading")) or f"Section {idx}"
        content = [_compress_text(item) for item in _to_string_list(raw.get("content", []))]
        numbers = [_safe_text(item) for item in _to_string_list(raw.get("numbers", []))]
        table = raw.get("table", [])
        table_rows = table if isinstance(table, list) else []

        normalized.append(
            {
                "heading": heading,
                "content": [item for item in content if item],
                "numbers": [item for item in numbers if item],
                "table": table_rows,
            }
        )
    return normalized


def _determine_target_slide_count(sections: list[dict[str, Any]]) -> int:
    complexity_score = len(sections)
    for section in sections:
        complexity_score += max(0, len(section["content"]) - 3) // 2
        if section["numbers"]:
            complexity_score += 1
        if section["table"]:
            complexity_score += 1

    return max(MIN_SLIDES, min(MAX_SLIDES, 8 + complexity_score // 2))


def _build_executive_summary(sections: list[dict[str, Any]]) -> list[str]:
    summary_points: list[str] = []

    for section in sections:
        if section["content"]:
            summary_points.append(section["content"][0])
        elif section["numbers"]:
            summary_points.append(
                f"{section['heading']}: numeric signals -> {', '.join(section['numbers'][:3])}"
            )

        if len(summary_points) >= MAX_BULLETS_PER_SLIDE:
            break

    if not summary_points:
        summary_points = ["Overview generated from parsed markdown input."]

    return summary_points[:MAX_BULLETS_PER_SLIDE]


def _build_chart_data(number_tokens: list[str]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for token in number_tokens:
        value = _to_numeric_value(token)
        if value is None:
            continue
        points.append({"label": token, "value": value})
        if len(points) >= MAX_CHART_POINTS:
            break
    return points


def _to_numeric_value(token: str) -> float | None:
    match = NUMERIC_TOKEN_RE.match(token)
    if not match:
        return None

    raw_value = match.group(2)
    suffix = (match.group(3) or "").lower()
    try:
        value = float(raw_value.replace(",", ""))
    except ValueError:
        return None

    if suffix == "%":
        return value / 100.0
    if suffix == "k":
        return value * 1_000
    if suffix == "m":
        return value * 1_000_000
    if suffix == "b":
        return value * 1_000_000_000
    return value


def _build_conclusion_points(sections: list[dict[str, Any]]) -> list[str]:
    points: list[str] = []
    for section in sections[:MAX_BULLETS_PER_SLIDE]:
        points.append(f"{section['heading']}: key points compiled for presentation.")

    if not points:
        points = ["Presentation generated from markdown input."]
    return points


def _detect_infographic_type(section: dict[str, Any]) -> str | None:
    content = section.get("content", [])
    heading = section.get("heading", "")
    if not isinstance(content, list):
        return None

    bullet_items = [item for item in content if str(item).strip().startswith("-")]
    numbered_items = [item for item in content if NUMBERED_STEP_RE.match(str(item).strip())]

    full_text = " ".join([heading] + [str(item) for item in content]).lower()

    has_timeline_signal = (
        "timeline" in full_text
        or "phase" in full_text
        or "roadmap" in full_text
        or bool(YEAR_RE.search(full_text))
    )
    has_two_group_signal = any(
        token in full_text for token in [" vs ", " versus ", "pros", "cons", "before", "after"]
    )
    has_two_group_signal = has_two_group_signal or _has_two_logical_groups(content)

    if numbered_items:
        return "process"
    if has_timeline_signal:
        return "timeline"
    if has_two_group_signal:
        return "two_column"
    if 3 <= len(bullet_items) <= 6:
        return "comparison"
    return None


def _has_two_logical_groups(content: list[str]) -> bool:
    groups = [item for item in content if ":" in str(item)]
    return len(groups) >= 2


def _make_filler_slide(sections: list[dict[str, Any]], index: int) -> dict[str, Any]:
    section = sections[index % len(sections)] if sections else {"heading": "Overview", "content": []}
    filler_content = section["content"][:MAX_BULLETS_PER_SLIDE] or [
        f"{section['heading']}: additional details can be elaborated in speaker notes."
    ]
    return {
        "type": "content",
        "title": f"{section['heading']} - Spotlight",
        "content": filler_content,
    }


def _trim_to_max(slides: list[dict[str, Any]], max_slides: int) -> list[dict[str, Any]]:
    if len(slides) <= max_slides:
        return slides

    # Keep first three high-priority slides and final conclusion.
    head = slides[:3]
    tail = [slides[-1]]
    middle = slides[3:-1]

    # Remove lower-priority slides first: chart/table, then extra content parts.
    priority_order = {"content": 0, "table": 1, "chart": 2}
    middle_sorted = sorted(
        enumerate(middle),
        key=lambda item: (priority_order.get(item[1].get("type", "content"), 3), item[0]),
    )

    keep_count = max_slides - len(head) - len(tail)
    kept_indices = sorted(index for index, _ in middle_sorted[:keep_count])
    kept_middle = [middle[i] for i in kept_indices]

    return head + kept_middle + tail


def _chunk_list(items: list[str], size: int) -> list[list[str]]:
    if size <= 0:
        return [items]
    return [items[i : i + size] for i in range(0, len(items), size)]


def _compress_text(text: str, max_len: int = 180) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


def _to_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
