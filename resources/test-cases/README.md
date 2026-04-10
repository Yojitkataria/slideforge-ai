## Test Files Package

This folder is ready to share and contains 5 markdown test inputs.

### What you still need from Hackathon drive
- `Slide Master/` templates (`.pptx`)
- `Sample Files/` reference markdown + expected outputs
- `Test Cases/` official markdown tests
- `Guidelines To be followed.pdf`
- `Common Mistakes and overall guide to improve slides.pptx`

### Recommended local structure
- `resources/slide-master/`
- `resources/sample-files/`
- `resources/test-cases/`
- `resources/guidelines/`
- `generated/` (store generated pptx outputs)

### Run generation for any test markdown
```bash
python main.py test-files/01_executive_overview.md
```

Then move/rename `output.pptx` into a matching folder under `generated/`.
