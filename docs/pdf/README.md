# OMNI-RANK Documentation PDFs

Two PDFs:

- `FEATURES.pdf` — every feature in the app: purpose, inputs, outputs, backend endpoints, external services, flow, screenshot slot.
- `TEST_SCENARIOS.pdf` — feature-by-feature QA tables (scenario · preconditions · steps · data inputs · expected result · priority) plus an end-to-end smoke test.

## Build

Prereqs (one-time):

```bash
sudo apt-get install -y pandoc       # or: brew install pandoc
pip install weasyprint
```

Build both:

```bash
cd docs/pdf
make
```

Output: `FEATURES.pdf` and `TEST_SCENARIOS.pdf` in the same folder.

## Add screenshots

Each section in `FEATURES.md` ends with a placeholder block like:

```html
<div class="screenshot-placeholder">screenshots/overview.png — ...</div>
```

To replace with a real screenshot, drop the PNG into `docs/pdf/screenshots/` using the filename in the placeholder, then change that block to standard Markdown:

```markdown
![Overview dashboard](./screenshots/overview.png)
```

Rebuild with `make`.

Suggested screenshots:

```
screenshots/sidebar.png
screenshots/overview.png
screenshots/projects.png
screenshots/workflow.png
screenshots/research.png
screenshots/keywords.png
screenshots/rank-tracker.png
screenshots/ai-visibility.png
screenshots/attribution.png
screenshots/competitors.png
screenshots/audit.png
screenshots/schema.png
screenshots/brief.png
screenshots/content.png
screenshots/programmatic.png
screenshots/links.png
screenshots/reports.png
screenshots/branding.png
screenshots/settings.png
screenshots/billing.png
```

## Styling

`print.css` controls the print layout. Highlights:

- Cover page on the first `<div class="cover">` block.
- A4 with running footer (page number + doc title).
- Gradient table headers, page-break-friendly rows.
- Priority pills (`p-critical`, `p-high`, `p-medium`, `p-low`) used in test tables.
- Screenshot placeholders render as hatched dashed blocks so empty slots are obvious before you drop the real images.
