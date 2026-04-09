import sys
from pathlib import Path

from parser.markdown_parser import parse_markdown
from planner.slide_planner import generate_slide_plan
from renderer.ppt_builder import build_ppt


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python main.py <markdown_file_path>")
        return

    markdown_path = Path(sys.argv[1])
    text = markdown_path.read_text(encoding="utf-8")
    parsed = parse_markdown(text)
    slide_plan = generate_slide_plan(parsed)
    output_path = build_ppt(slide_plan, "output.pptx")
    print(f"PPT created: {output_path}")


if __name__ == "__main__":
    main()
