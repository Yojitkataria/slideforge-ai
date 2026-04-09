"""Markdown parser for SlideForge AI (Prompt 2)."""

from __future__ import annotations

import re
from typing import Any

import markdown
from bs4 import BeautifulSoup, Tag


NUMERIC_RE = re.compile(
    r"(?<![\w.])([$€£₹])?\s*([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(%|k|m|b)?(?!\w)",
    re.IGNORECASE,
)


def parse_markdown(text: str) -> dict[str, Any]:
    """
    Convert markdown text into structured JSON.

    Output format:
    {
      "title": "",
      "sections": [
        {
          "heading": "",
          "content": [],
          "numbers": [],
          "table": []
        }
      ]
    }
    """
    html = markdown.markdown(text or "", extensions=["tables", "sane_lists"])
    soup = BeautifulSoup(html, "html.parser")

    title = _extract_title(soup)
    sections = _extract_sections(soup)
    return {"title": title, "sections": sections}


def _extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)

    first_text = soup.get_text(" ", strip=True)
    return first_text if first_text else "Untitled Presentation"


def _extract_sections(soup: BeautifulSoup) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []

    active_section = _new_section("Introduction")
    seen_content = False

    for node in soup.find_all(["h2", "h3", "p", "ul", "ol", "table"], recursive=True):
        if not isinstance(node, Tag):
            continue

        if node.name in {"h2", "h3"}:
            # Finalize previous section if it has any content.
            if seen_content or active_section["heading"] != "Introduction":
                _dedupe_section_numbers(active_section)
                sections.append(active_section)

            heading = node.get_text(" ", strip=True) or "Untitled Section"
            active_section = _new_section(heading)
            seen_content = False
            continue

        _consume_node_into_section(node, active_section)
        seen_content = True

    # Push final section if any content exists.
    if seen_content or active_section["heading"] != "Introduction":
        _dedupe_section_numbers(active_section)
        sections.append(active_section)

    return sections


def _consume_node_into_section(node: Tag, section: dict[str, Any]) -> None:
    if node.name == "p":
        text = node.get_text(" ", strip=True)
        if text:
            section["content"].append(text)
            section["numbers"].extend(_extract_numbers(text))
        return

    if node.name == "ul":
        for li in node.find_all("li", recursive=False):
            item = li.get_text(" ", strip=True)
            if not item:
                continue
            section["content"].append(f"- {item}")
            section["numbers"].extend(_extract_numbers(item))
        return

    if node.name == "ol":
        idx = 1
        for li in node.find_all("li", recursive=False):
            item = li.get_text(" ", strip=True)
            if not item:
                continue
            section["content"].append(f"{idx}. {item}")
            section["numbers"].extend(_extract_numbers(item))
            idx += 1
        return

    if node.name == "table":
        parsed_rows = _parse_table(node)
        if parsed_rows:
            section["table"].extend(parsed_rows)
            for row in parsed_rows:
                for value in row.values():
                    section["numbers"].extend(_extract_numbers(str(value)))


def _parse_table(table_node: Tag) -> list[dict[str, str]]:
    headers: list[str] = []
    rows: list[dict[str, str]] = []

    header_cells = table_node.select("thead tr th")
    if header_cells:
        headers = [cell.get_text(" ", strip=True) for cell in header_cells]
    else:
        first_row = table_node.find("tr")
        if first_row:
            headers = [cell.get_text(" ", strip=True) for cell in first_row.find_all(["th", "td"])]

    body_rows = table_node.select("tbody tr")
    if not body_rows:
        # Fallback for tables without explicit <tbody>
        all_rows = table_node.find_all("tr")
        body_rows = all_rows[1:] if len(all_rows) > 1 else []

    for tr in body_rows:
        cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"])]
        if not cells:
            continue

        row_dict: dict[str, str] = {}
        for i, cell_text in enumerate(cells):
            key = headers[i] if i < len(headers) and headers[i] else f"col_{i + 1}"
            row_dict[key] = cell_text
        rows.append(row_dict)

    return rows


def _extract_numbers(text: str) -> list[str]:
    numbers: list[str] = []
    for match in NUMERIC_RE.finditer(text):
        currency = match.group(1) or ""
        value = match.group(2) or ""
        suffix = match.group(3) or ""
        numbers.append(f"{currency}{value}{suffix}")
    return numbers


def _dedupe_section_numbers(section: dict[str, Any]) -> None:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in section["numbers"]:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    section["numbers"] = deduped


def _new_section(heading: str) -> dict[str, Any]:
    return {"heading": heading, "content": [], "numbers": [], "table": []}
