"""Batch-generate PPTX files for all markdown test cases."""

from __future__ import annotations

import shutil
from pathlib import Path

from parser.markdown_parser import parse_markdown
from planner.slide_planner import generate_slide_plan
from renderer.ppt_builder import build_ppt


MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
ROOT_DIR = Path(__file__).resolve().parent
INPUT_DIR = ROOT_DIR / "resources" / "test-cases"
OUTPUT_DIR = ROOT_DIR / "generated"
TEMPLATES_DIR = ROOT_DIR / "templates"


def _resolve_template() -> str | None:
    """Resolve the best available template path, if any."""
    preferred = [
        TEMPLATES_DIR / "default.pptx",
        TEMPLATES_DIR / "template.pptx",
    ]
    for candidate in preferred:
        if candidate.exists():
            return str(candidate)

    other_templates = sorted(TEMPLATES_DIR.glob("*.pptx"))
    if other_templates:
        return str(other_templates[0])
    return None


def _collect_markdown_files(directory: Path) -> list[Path]:
    """Return all markdown files under the target directory."""
    patterns = ("*.md", "*.markdown")
    files: list[Path] = []
    for pattern in patterns:
        files.extend(directory.rglob(pattern))
    return sorted(set(files))


def run_batch_generation() -> int:
    """Run markdown -> pptx generation for all test case files."""
    print("[INFO] SlideForge AI batch generation started")
    print(f"[INFO] Input directory: {INPUT_DIR}")
    print(f"[INFO] Output directory: {OUTPUT_DIR}")

    if not INPUT_DIR.exists():
        print("[ERROR] Input directory does not exist. Create 'resources/test-cases/' first.")
        return 1

    markdown_files = _collect_markdown_files(INPUT_DIR)
    if not markdown_files:
        print("[WARN] No markdown files found in resources/test-cases/")
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    template_path = _resolve_template()
    if template_path:
        print(f"[INFO] Using template: {template_path}")
    else:
        print("[WARN] No template found in /templates. Falling back to renderer defaults.")

    processed = 0
    skipped = 0
    failed = 0
    case_number = 1

    for md_file in markdown_files:
        size = md_file.stat().st_size
        if size > MAX_FILE_SIZE_BYTES:
            skipped += 1
            print(
                f"[SKIP] {md_file.name}: file size {size / (1024 * 1024):.2f}MB exceeds 5MB limit"
            )
            continue

        case_dir = OUTPUT_DIR / f"case_{case_number:02d}"
        case_dir.mkdir(parents=True, exist_ok=True)
        copied_md_path = case_dir / "input.md"
        output_ppt_path = case_dir / "output.pptx"

        print(f"[INFO] Processing {md_file.name} -> {case_dir.name}")
        try:
            shutil.copy2(md_file, copied_md_path)

            markdown_text = md_file.read_text(encoding="utf-8")
            parsed = parse_markdown(markdown_text)
            slide_plan = generate_slide_plan(parsed)
            build_ppt(slide_plan, str(output_ppt_path), template_path)

            processed += 1
            case_number += 1
            print(f"[OK] Generated: {output_ppt_path}")
        except Exception as exc:  # noqa: BLE001 - continue remaining files
            failed += 1
            print(f"[ERROR] Failed for {md_file.name}: {exc}")
            continue

    print("\n[INFO] Batch generation complete")
    print(f"[INFO] Processed: {processed}")
    print(f"[INFO] Skipped (>5MB): {skipped}")
    print(f"[INFO] Failed: {failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(run_batch_generation())
