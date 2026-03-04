# Project: Corporate Tax Research 2026

## Purpose

Interactive web tool and data pipeline for analysing the total economic tax contribution of Australia's largest corporations. Goes beyond corporate income tax to include employment-generated taxes (PAYG, payroll, Medicare, super, GST). Built on the PwC Total Tax Contribution framework.

**Live URL:** https://hk121992.github.io/corporate-tax-research-2026/

## Tech Stack

- Language: Python 3.8+ (data pipeline), vanilla JavaScript (web app)
- Framework: None — pure stdlib + Chart.js for visualisation
- Database: None (JSON datasets)
- Key dependencies:
  - Python: `requests`, `pandas`, `openpyxl`
  - Frontend: Chart.js 3.x (bundled UMD)

## Project Structure

```
config/              # Tax rate configs by financial year (JSON)
data/
  enriched/          # Manually curated company data (CSV, 51 companies)
  reference/         # ABS salary + GST reference data (JSON)
  processed/         # Final computed datasets (JSON)
  raw/               # [gitignored] ATO downloads
pipeline/
  fetch_ato_data.py  # Download ATO data via CKAN API
  calculate_taxes.py # Core tax estimation functions
  build_dataset.py   # Merge enriched + ATO → processed JSON
  build_historical_datasets.py  # Generate FY2019-20 to FY2022-23
  gen_data_report.py # HTML data report
webapp/              # Interactive web app (Chart.js)
  index.html         # Main page
  app.js             # Charts, interactivity (~2300 lines)
  style.css          # Responsive design
  dataset_*.js       # Pre-built datasets (loaded by browser)
docs/                # GitHub Pages mirror — MUST stay in sync with webapp/
```

## Workflows

- **Dev server**: Open `webapp/index.html` in a browser (or `python3 -m http.server -d webapp`)
- **Pipeline**: `pip install -r requirements.txt && python pipeline/build_dataset.py`
- **Historical data**: `python pipeline/build_historical_datasets.py`
- **Deploy**: Push to GitHub — `docs/` is served by GitHub Pages automatically
- **Test**: Manual testing only (no test framework)
- **Lint**: None configured

## Important Notes

- **Keep `webapp/` and `docs/` in sync!** After modifying webapp files, copy them to docs/ before committing. GitHub Pages serves from `docs/`.
- No API keys required — ATO CKAN API is public
- The enriched CSV (`data/enriched/companies_enriched.csv`) is manually curated from company annual reports
- Tax calculations correct for Jensen's inequality using 5-quintile salary distributions

## Rules

- Always read `claude-progress.txt` first to understand current state
- Always update `claude-progress.txt` after completing a task
- Always update `docs/progress.md` with a session entry when done
- Never modify files outside this project's directory
- Ask before deleting files or making breaking changes
- Ask before adding new dependencies
- Commit work with clear messages referencing the task from the session brief

## Session Handoff (MANDATORY)

These three steps must be completed before any `git commit`. If the PM says "wrap up" or "handoff" at any point, complete these steps immediately even if objectives are unfinished.

### 1. Write `handoff.md` to the project root

Overwrite (or create) `handoff.md` — this file is gitignored. Middle Management reads it on re-entry.

```markdown
# Handoff — corporate-tax-research-2026 — [YYYY-MM-DD HH:MM]

## Status
[One sentence: current state]

## Completed
- [task]: [result/done/partial]

## Not Completed
- [task]: [why not — or "None"]

## Key Finding
[The single most important result or discovery. Include numbers where relevant.]

## Next Action
[Exactly what should happen next — specific enough to act on]

## Blockers / Decisions Needed
[Specific blockers, or "None"]

## Commit
[hash] — [message]
```

### 2. Update `claude-progress.txt`

Replace the entire contents:

```
Last updated: [YYYY-MM-DD]
Branch: [branch name]
Status: [one line summary]

Completed this session:
- [task]: [done / partial / blocked]

Next:
- [what should happen next]

Blockers / Decisions needed:
- [any, or "None"]
```

### 3. Append to `docs/progress.md`

Add a new entry at the top:

```markdown
## [YYYY-MM-DD] — [Session title]

**Completed:** [task list]
**Not completed:** [anything skipped or blocked, or "None"]

**Key Finding:**
[Same as handoff.md Key Finding]

**Decisions informed:** [Did findings change what to build? Or "None."]

**Files modified:** [list]
**Commit:** [hash]
```

### 4. Commit

Commit all work including `claude-progress.txt` and `docs/progress.md`. Do **not** commit `handoff.md` — it is gitignored.

## Context Files

- `claude-progress.txt` — Quick-resume: current state, last session, next steps
- `docs/plan.md` — Living project plan with milestones and tasks
- `docs/decisions.md` — All decisions made for this project
- `docs/progress.md` — Session-by-session progress log

## Managed By

This project is managed by the Middle Management system at `~/projects/Middle-management/`.
Session briefs and coordination come from there. If you need a decision that isn't covered
by existing decisions, create a note in the progress update — the management agent will
route it to the product manager.
