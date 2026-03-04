# Corporate Tax Research 2026 — Decision Log

## Pre-MM Decisions

### PwC TTC Framework
**Decision:** Use the PwC Total Tax Contribution framework as the methodological basis.
**Rationale:** Industry-standard approach for measuring total economic tax contribution beyond just corporate income tax.

### Client-side only (GitHub Pages)
**Decision:** No backend server — all computation pre-baked into JSON datasets, visualised in browser.
**Rationale:** Simplifies deployment, no hosting costs, accessible to anyone with the URL.

### Manual company enrichment
**Decision:** Manually curate company data (employee counts, state distribution, salary estimates) from annual reports into a CSV.
**Rationale:** No reliable API for Australian company employment data. ATO transparency data only covers income tax paid.
