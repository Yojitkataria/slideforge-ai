import tempfile
import sys
from pathlib import Path
from typing import Any

import gradio as gr

# Allow direct execution via `python ui/app.py`.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from parser.markdown_parser import parse_markdown
from planner.slide_planner import generate_slide_plan
from renderer.ppt_builder import build_ppt


def _resolve_file_path(file_input: Any) -> str | None:
    if file_input is None:
        return None
    if isinstance(file_input, str):
        return file_input
    file_name = getattr(file_input, "name", None)
    if isinstance(file_name, str):
        return file_name
    return None


def generate(md_file: Any, template_file: Any) -> str:
    md_path = _resolve_file_path(md_file)
    if not md_path:
        raise gr.Error("Please upload a markdown file.")

    text = Path(md_path).read_text(encoding="utf-8")
    parsed = parse_markdown(text)
    slide_plan = generate_slide_plan(parsed)

    output = tempfile.NamedTemporaryFile(delete=False, suffix=".pptx")
    output.close()

    template_path = _resolve_file_path(template_file)
    build_ppt(slide_plan, output.name, template_path)
    return output.name


ui = gr.Interface(
    fn=generate,
    inputs=[
        gr.File(label="Upload Markdown (.md)"),
        gr.File(label="Upload Template PPT (optional)"),
    ],
    outputs=gr.File(label="Download PPTX"),
    title="SlideForge AI",
    description="Upload markdown and generate PPT using AI",
)


if __name__ == "__main__":
    ui.launch(share=True)
