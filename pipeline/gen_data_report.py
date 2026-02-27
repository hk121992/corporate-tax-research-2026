"""Generate docs/data_report.html — static summary report."""
import json, os

BASE = "/home/user/corporate-tax-research-2026"

# Parse datasets
datasets = {}
for yr, js_yr in [("2019-20","2019_20"),("2020-21","2020_21"),("2021-22","2021_22"),("2022-23","2022_23"),("2023-24","2023_24")]:
    path = os.path.join(BASE, "docs", f"dataset_{js_yr}.js")
    with open(path) as f:
        content = f.read()
    # Strip JS wrapper: find the `= {` assignment, use json decoder from `{`
    import re as _re
    m = _re.search(r'window\.__DATASETS__\[".+?"\]\s*=\s*(\{)', content)
    start = m.start(1)
    # decode only the JSON object (json.JSONDecoder handles partial strings)
    import json as _json
    data, _ = _json.JSONDecoder().raw_decode(content, start)
    datasets[yr] = data

# Aggregate rows
rows_agg = ""
for yr, ds in datasets.items():
    a = ds["aggregates"]
    n = ds["meta"]["company_count"]
    corp = a["total_corporate_income_tax"]
    ttc  = a["total_tax_contribution_core"]
    emp  = a["total_employees_au"]
    mult = a["avg_employment_multiplier"]
    res  = a.get("total_resource_payments_to_crown", 0)
    ratio = ttc/corp if corp else 0
    rows_agg += (
        f"<tr>"
        f"<td>FY {yr}</td>"
        f"<td class='num'>{n}</td>"
        f"<td class='num'>${corp/1e9:.1f}B</td>"
        f"<td class='num'>${ttc/1e9:.1f}B</td>"
        f"<td class='num'>{ratio:.2f}&times;</td>"
        f"<td class='num'>{emp:,}</td>"
        f"<td class='num'>{mult:.2f}&times;</td>"
        f"<td class='num'>${res/1e9:.1f}B</td>"
        f"</tr>\n"
    )

# Company rows for FY2023-24
ds_latest = datasets["2023-24"]
rows_co = ""
for c in sorted(ds_latest["companies"], key=lambda x: -x["totals"]["total_ttc_core"])[:20]:
    co   = c["company"]
    ind  = " ".join(c["industry"].split()[:2])
    emp  = c["employment"]["employees_au"]
    corp = c["taxes_borne"]["corporate_income_tax"]
    ttc  = c["totals"]["total_ttc_core"]
    mult = c["metrics"]["employment_tax_multiplier"]
    rev  = c["ato_data"]["total_income"]
    rpe  = c["metrics"]["revenue_per_employee_aud"]
    src  = "ATO" if c["ato_data"]["is_ato_actual"] else "est."
    mult_str = f"{mult:.2f}&times;" if mult else "&mdash;"
    rows_co += (
        f"<tr>"
        f"<td>{co}</td>"
        f"<td>{ind}</td>"
        f"<td class='num'>{emp:,}</td>"
        f"<td class='num'>${rev/1e9:.1f}B</td>"
        f"<td class='num'>${corp/1e9:.2f}B <small class='src'>{src}</small></td>"
        f"<td class='num'>${ttc/1e9:.2f}B</td>"
        f"<td class='num'>{mult_str}</td>"
        f"<td class='num'>${rpe/1e3:.0f}K</td>"
        f"</tr>\n"
    )

CSS = """
  :root { --navy:#1a3a5c; --blue:#2e6da4; --light:#f7f8fc; --border:#dde1ea; --text:#2d2d4a; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, -apple-system, sans-serif; font-size: 14px;
         color: var(--text); background: var(--light); line-height: 1.5; }
  .page { max-width: 1100px; margin: 0 auto; padding: 2rem 1.5rem; }
  h1 { font-size: 1.6rem; color: var(--navy); margin-bottom: 0.25rem; }
  h2 { font-size: 1.1rem; color: var(--navy); margin: 2rem 0 0.75rem; padding-bottom: 0.4rem;
       border-bottom: 2px solid var(--blue); }
  .meta { font-size: 0.8rem; color: #777; margin-bottom: 1.5rem; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 1.5rem;
          background: #fff; border-radius: 8px; overflow: hidden;
          box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
  thead { background: var(--navy); color: #fff; }
  th { padding: 0.6rem 0.75rem; text-align: left; font-size: 0.78rem; font-weight: 600; }
  td { padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); font-size: 0.82rem; }
  tr:last-child td { border-bottom: none; }
  tr:nth-child(even) { background: #f8fafd; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  .src { color: #888; font-size: 0.7rem; }
  .section-note { font-size: 0.79rem; color: #555; margin: -0.25rem 0 1rem; }
  .badge-ato { background:#d4edda;color:#155724;padding:1px 5px;border-radius:3px;font-size:0.7rem;font-weight:700; }
  .badge-est { background:#fff3cd;color:#856404;padding:1px 5px;border-radius:3px;font-size:0.7rem; }
  footer { font-size: 0.72rem; color: #aaa; margin-top: 2rem; padding-top: 1rem;
           border-top: 1px solid var(--border); }
  ul { margin-left: 1.25rem; margin-bottom: 1rem; line-height: 2; }
  @media (max-width:700px) { th, td { padding: 0.4rem 0.5rem; font-size: 0.75rem; } }
"""

METHOD_ROWS = """
    <tr><td>Corporate income tax</td><td>Taxes Borne &mdash; actual/est.</td>
        <td>ATO transparency data where matched; annual report estimate otherwise</td>
        <td>ATO Corporate Tax Transparency Report 2023&ndash;24</td></tr>
    <tr><td>Employer payroll tax</td><td>Taxes Borne &mdash; estimated</td>
        <td>max(0, state_wages &minus; state_threshold) &times; state_rate</td>
        <td>State Revenue Offices &mdash; payrolltax.gov.au</td></tr>
    <tr><td>Employee income tax (PAYG)</td><td>Taxes Collected &mdash; estimated</td>
        <td>5-quintile salary distribution per industry. E[tax(salary)] = &Sigma; 0.2 &times; tax(salary_q)</td>
        <td>ABS Employee Earnings, Hours and Leave Survey (EEH)</td></tr>
    <tr><td>Medicare levy</td><td>Taxes Collected &mdash; estimated</td>
        <td>2% of gross salary across quintile distribution</td>
        <td>ATO income tax rates</td></tr>
    <tr><td>GST from employee spending</td><td>Taxes Collected &mdash; estimated</td>
        <td>after_tax &times; 75% consumption &times; GST coverage (38&ndash;47%) &times; (10/110)</td>
        <td>ABS Household Expenditure Survey 2021&ndash;22</td></tr>
    <tr><td>Land tax (optional)</td><td>Taxes Borne &mdash; rough estimate</td>
        <td>employees &times; homeownership_rate &times; median_land_value &times; effective_rate. Disabled by default.</td>
        <td>REIA, state revenue offices</td></tr>
    <tr><td>Resource payments</td><td>NOT a tax</td>
        <td>Royalties + PRRT paid to government as resource owner. Separate from tax totals.</td>
        <td>Company annual reports</td></tr>
"""

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Data Report &mdash; Corporate Tax Research 2026 &middot; Australia</title>
<style>{CSS}</style>
</head>
<body>
<div class="page">

<h1>Corporate Tax Research 2026 &mdash; Data Report</h1>
<p class="meta">
  PwC Total Tax Contribution (TTC) Framework &middot;
  Australia &middot;
  FY2019&ndash;20 to FY2023&ndash;24 &middot;
  Top-20 ASX / large-company panel &middot;
  Generated: 2026-02-27
</p>

<h2>1. Five-Year Aggregate Summary</h2>
<p class="section-note">
  Corporate income tax = ATO Corporate Tax Transparency data where available; otherwise estimated from
  annual reports. All employment-linked tax figures are modelled estimates.
  Resource payments (royalties, PRRT) are <em>not</em> taxes.
</p>
<table>
  <thead>
    <tr>
      <th>Year</th><th>Companies</th><th>Corp Tax</th><th>Total TTC</th>
      <th>TTC / Corp Tax</th><th>AU Employees</th>
      <th>Avg Multiplier</th><th>Resource Pmts</th>
    </tr>
  </thead>
  <tbody>{rows_agg}</tbody>
</table>

<h2>2. FY2023&ndash;24 Company Detail (Top 20 by TTC)</h2>
<p class="section-note">
  Sorted by Total TTC descending. <span class="badge-ato">ATO</span> = ATO Corporate Tax Transparency;
  <span class="badge-est">est.</span> = annual report estimate.
</p>
<table>
  <thead>
    <tr>
      <th>Company</th><th>Industry</th><th>Employees (AU)</th>
      <th>Revenue</th><th>Corp Tax</th><th>Total TTC</th>
      <th>Multiplier</th><th>Rev / Employee</th>
    </tr>
  </thead>
  <tbody>{rows_co}</tbody>
</table>

<h2>3. Methodology Notes</h2>
<table>
  <thead><tr><th>Component</th><th>Type</th><th>Method</th><th>Source</th></tr></thead>
  <tbody>{METHOD_ROWS}</tbody>
</table>

<h2>4. Data Sources</h2>
<ul>
  <li>ATO Corporate Tax Transparency Report 2023&ndash;24 &mdash; ato.gov.au</li>
  <li>ABS Employee Earnings, Hours and Leave Survey (EEH) 2023&ndash;24 &mdash; abs.gov.au</li>
  <li>ABS Household Expenditure Survey 2021&ndash;22 &mdash; abs.gov.au</li>
  <li>State Revenue Offices (NSW, VIC, QLD, WA, SA, ACT, NT, TAS) payroll tax rates &amp; thresholds</li>
  <li>PwC Total Tax Contribution (TTC) Framework (2005&ndash;present)</li>
  <li>OECD Taxing Wages 2025 (tax wedge methodology)</li>
  <li>Company annual reports FY2019&ndash;20 through FY2023&ndash;24 (ASX disclosures)</li>
  <li>Grattan Institute &mdash; capital vs labour income share research</li>
  <li>OECD Corporate Tax Statistics 2024</li>
</ul>

<footer>
  Corporate Tax Research 2026 &middot;
  github.com/hk121992/corporate-tax-research-2026 &middot;
  Disclaimer: Employment-linked tax figures are modelled estimates, not actual liabilities.
  Superannuation contributions (SGC rate per year) excluded &mdash; deferred compensation, not taxes.
</footer>

</div>
</body>
</html>
"""

out = os.path.join(BASE, "docs", "data_report.html")
with open(out, "w") as f:
    f.write(html)
print(f"Written: {out}  ({os.path.getsize(out)/1024:.1f} KB)")
