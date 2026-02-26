/**
 * app.js — Corporate Tax Research 2026 Web App
 *
 * Loads the dataset (from window.__DATASETS__ set by dataset_2023_24.js),
 * renders three Chart.js visualisations and a sortable data table.
 *
 * Tax component toggles update all charts and table figures live.
 *
 * Framework: PwC Total Tax Contribution (TTC):
 *   Taxes Borne  = corporate income tax + employer payroll tax (+ land tax if enabled)
 *   Taxes Collected = employee income tax + Medicare levy + GST from spending (est.)
 *   Total TTC    = Taxes Borne + Taxes Collected
 */

"use strict";

/* =====================================================================
   CONSTANTS & COLOUR SCHEME
   ===================================================================== */

const TAX_COMPONENTS = [
  {
    id:      "corporate_income_tax",
    label:   "Corporate income tax",
    tag:     "actual",
    color:   "#1a3a5c",
    category: "taxes_borne",
    defaultOn: true,
    tooltip: "ATO Corporate Tax Transparency data.\nActual tax payable reported to the ATO.",
  },
  {
    id:      "employer_payroll_tax",
    label:   "Employer payroll tax",
    tag:     "est",
    color:   "#2e6da4",
    category: "taxes_borne",
    defaultOn: true,
    tooltip: "Estimated state payroll tax.\nFormula: (employees × avg_salary − state_threshold) × state_rate.\nRates: NSW 5.45%, VIC 4.85%, QLD 4.75%, WA 5.5%.",
  },
  {
    id:      "employee_income_tax_withheld",
    label:   "Employee income tax",
    tag:     "est",
    color:   "#4a9fd4",
    category: "taxes_collected",
    defaultOn: true,
    tooltip: "Estimated PAYG withholding.\nUses 5-quintile salary distribution per industry\n(corrects for Jensen's inequality on progressive brackets).\nSource: ABS Employee Earnings & Hours Survey.",
  },
  {
    id:      "employee_medicare_levy",
    label:   "Employee Medicare levy",
    tag:     "est",
    color:   "#3a9a5c",
    category: "taxes_collected",
    defaultOn: true,
    tooltip: "Estimated Medicare levy (2% of gross salary).\nSource: ATO income tax rates.",
  },
  {
    id:      "employee_gst_spending_estimate",
    label:   "GST from employee spending",
    tag:     "est",
    color:   "#d4880e",
    category: "taxes_collected",
    defaultOn: true,
    tooltip: "Estimated GST paid by employees as consumers.\nFormula: after_tax × consumption_rate × gst_coverage × (10/110).\nGST coverage: 38–44% of spending by income band.\nSource: ABS Household Expenditure Survey 2021-22.",
  },
  {
    id:      "land_tax_estimate",
    label:   "Land tax (employees)",
    tag:     "rough",
    color:   "#c0392b",
    category: "taxes_borne",
    defaultOn: false,
    tooltip: "ROUGH ESTIMATE — highly variable.\nResidential land tax paid by employees who own property.\nFormula: employees × homeownership_rate × median_land_value × effective_rate.\nDisabled by default.",
  },
  {
    id:       "resource_payments_to_crown",
    label:    "Resource payments to Crown",
    tag:      "resource",
    color:    "#7b3f00",
    category: "resource_payments",
    defaultOn: false,
    tooltip:  "Royalties + PRRT paid to government as resource owner.\nNOT a tax — government receives as owner of the resource.\nOnly applies to mining/petroleum companies.\nRoyalties: state-based charges on extracted commodities.\nPRRT: Petroleum Resource Rent Tax on petroleum profits.\nSource: company annual reports FY2023–24.",
  },
];

const INDUSTRY_COLOURS = {
  "Mining":                          "#f5a623",
  "Finance and Insurance Services":  "#27ae60",
  "Retail Trade":                    "#2980b9",
  "Health Care and Social Assistance":"#e74c3c",
  "Information Media and Telecommunications": "#8e44ad",
  "Transport Postal and Warehousing":"#16a085",
  "Construction":                    "#d35400",
  "Electricity Gas Water and Waste Services": "#2ecc71",
  "Finance and Insurance":           "#27ae60",
};

function industryColor(industry) {
  for (const [key, color] of Object.entries(INDUSTRY_COLOURS)) {
    if (industry.includes(key.split(" ")[0])) return color;
  }
  return "#95a5a6";
}

function industryClass(industry) {
  if (industry.includes("Mining"))         return "industry-Mining";
  if (industry.includes("Finance"))        return "industry-Finance";
  if (industry.includes("Retail"))         return "industry-Retail";
  if (industry.includes("Health"))         return "industry-Health";
  if (industry.includes("Information") || industry.includes("Media") || industry.includes("Telecom")) return "industry-Tech";
  if (industry.includes("Transport"))      return "industry-Transport";
  if (industry.includes("Construction"))   return "industry-Construction";
  if (industry.includes("Electricity") || industry.includes("Energy")) return "industry-Energy";
  if (industry.includes("Property") || industry.includes("REIT")) return "industry-Property";
  return "industry-Other";
}

/* =====================================================================
   SHAREHOLDER CAPITAL RETURNS DATA — FY 2023–24
   Source: Company annual reports & ASX disclosures.
   Values in AUD. Calendar-year reporters (Rio Tinto, Newmont) use
   full-year 2023 actuals converted at prevailing AUD/USD rates.
   Methodology note: "capital returned" = dividends paid + on/off-market
   buybacks. Total Shareholder Return (TSR) including price appreciation
   is a broader measure; this captures the cash returned to shareholders,
   the most direct comparator to tax payments. Government-owned entities
   (Australia Post) have no public capital return.
   Research context: Grattan Institute (capital vs labour income shares),
   Australia Institute (corporate income distribution), OECD Corporate
   Tax Statistics 2024, Zucman et al. on corporate profit distribution.
   ===================================================================== */

const SHAREHOLDER_CAPITAL_RETURNS_2023_24 = {
  // { d: dividends_aud, b: buybacks_aud }
  "commonwealth-bank-of-australia":     { d: 8.60e9, b: 0.50e9 },
  "bhp-group":                          { d: 10.0e9, b: 4.00e9 }, // USD conv; reduced vs FY22/23 peak
  "rio-tinto":                          { d: 12.0e9, b: 2.00e9 }, // CY2023; USD conv
  "westpac-banking-corporation":        { d: 3.50e9, b: 1.50e9 },
  "anz-banking-group":                  { d: 3.20e9, b: 0.20e9 },
  "national-australia-bank":            { d: 3.60e9, b: 1.50e9 },
  "fortescue-metals-group":             { d: 6.10e9, b: 0      },
  "woolworths-group":                   { d: 1.10e9, b: 0      },
  "wesfarmers":                         { d: 1.60e9, b: 0      },
  "woodside-energy-group":              { d: 3.40e9, b: 0      },
  "coles-group":                        { d: 0.90e9, b: 0      },
  "macquarie-group":                    { d: 1.50e9, b: 0.20e9 },
  "telstra-corporation":                { d: 0.60e9, b: 0.80e9 },
  "australia-post":                     { d: 0,      b: 0      }, // Gov-owned; no public dividend FY24
  "downer-group":                       { d: 0.20e9, b: 0      },
  "qantas-airways":                     { d: 0.30e9, b: 0.40e9 },
  "insurance-australia-group":          { d: 0.60e9, b: 0      },
  "cimic-group-cpb-contractors":        { d: 0.40e9, b: 0      },
  "suncorp-group":                      { d: 0.70e9, b: 0      },
  "csl-limited":                        { d: 1.50e9, b: 0.50e9 }, // USD conv
  "bluescope-steel":                    { d: 0.25e9, b: 0.20e9 },
  "santos":                             { d: 0.70e9, b: 0.20e9 },
  "origin-energy":                      { d: 0.60e9, b: 0      },
  "south32":                            { d: 1.20e9, b: 0.40e9 },
  "ampol-formerly-caltex":             { d: 0.60e9, b: 0.10e9 },
  "sonic-healthcare":                   { d: 0.35e9, b: 0      },
  "endeavour-group":                    { d: 0.50e9, b: 0      },
  "agl-energy":                         { d: 0.20e9, b: 0      },
  "scentre-group":                      { d: 0.80e9, b: 0      }, // REIT distributions
  "lendlease-group":                    { d: 0.15e9, b: 0      },
  "incitec-pivot-dyno-nobel":           { d: 0.35e9, b: 0.10e9 },
  "harvey-norman-holdings":             { d: 0.50e9, b: 0      },
  "newmont-formerly-newcrest":          { d: 0.50e9, b: 0      }, // USD conv; global
  "viva-energy-group":                  { d: 0.60e9, b: 0      },
  "jb-hi-fi":                           { d: 0.40e9, b: 0      },
  "medibank-private":                   { d: 0.55e9, b: 0.10e9 },
  "rea-group":                          { d: 0.35e9, b: 0      },
  "amp-limited":                        { d: 0.20e9, b: 0      },
  "transurban-group":                   { d: 1.10e9, b: 0      }, // Infrastructure distributions
  "seek-limited":                       { d: 0.10e9, b: 0      },
  "stockland-corporation":              { d: 0.40e9, b: 0      }, // REIT
  "nine-entertainment":                 { d: 0.10e9, b: 0      },
  "gpt-group":                          { d: 0.35e9, b: 0      }, // REIT
  "afterpay---block-au":               { d: 0,      b: 0.30e9 }, // Growth; USD buyback conv
  "wisetech-global":                    { d: 0.04e9, b: 0      },
  "atlassian-au-australian-operations": { d: 0,      b: 0      }, // US-hq growth; no AU dividends
  "car-group-carsales.com":            { d: 0.20e9, b: 0      },
  "myer-holdings":                      { d: 0.08e9, b: 0      },
  "xero":                               { d: 0,      b: 0      }, // Growth; no dividends
};

function getCapitalReturns(company) {
  const d = SHAREHOLDER_CAPITAL_RETURNS_2023_24[company.id];
  if (!d) return { dividends: 0, buybacks: 0, total: 0 };
  return {
    dividends: d.d || 0,
    buybacks:  d.b || 0,
    total:     (d.d || 0) + (d.b || 0),
  };
}

/* =====================================================================
   STATE
   ===================================================================== */

let allCompanies = [];
let filteredCompanies = [];
let charts = {};
let sortState = { key: "total_ttc", dir: "desc" };

let activeToggles = new Set(TAX_COMPONENTS.filter(t => t.defaultOn).map(t => t.id));
let activeFilter = "all";
let viewMode = "total"; // "total" | "per_employee"
let topN = 20;

/* =====================================================================
   HELPERS — CALCULATIONS
   ===================================================================== */

function computeTotals(company) {
  /**
   * Given the current active toggles, compute the effective total
   * for a company. Returns an object with per-component values and total.
   */
  const values = {};
  let total = 0;

  for (const comp of TAX_COMPONENTS) {
    const isActive = activeToggles.has(comp.id);
    let val = 0;
    if (comp.category === "taxes_borne") {
      val = company.taxes_borne?.[comp.id] ?? 0;
    } else if (comp.category === "resource_payments") {
      val = company.resource_payments_to_crown?.total ?? 0;
    } else {
      val = company.taxes_collected?.[comp.id] ?? 0;
    }
    values[comp.id] = isActive ? val : 0;
    if (isActive) total += val;
  }

  const empCount = company.employment?.employees_au ?? 1;
  const corpTax  = company.taxes_borne?.corporate_income_tax ?? 0;

  return {
    values,
    total,
    perEmployee: empCount > 0 ? total / empCount : 0,
    multiplier:  corpTax > 0  ? total / corpTax  : null,
  };
}

function fmtBillions(v) {
  if (v == null) return "—";
  const b = v / 1e9;
  if (b >= 10)  return "$" + b.toFixed(1) + "B";
  if (b >= 1)   return "$" + b.toFixed(2) + "B";
  const m = v / 1e6;
  if (m >= 10)  return "$" + m.toFixed(0) + "M";
  if (m >= 1)   return "$" + m.toFixed(1) + "M";
  return "$" + (v / 1e3).toFixed(0) + "K";
}

function fmtNum(v, decimals = 0) {
  if (v == null) return "—";
  return v.toLocaleString("en-AU", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function fmtPct(v) {
  if (v == null) return "—";
  return (v * 100).toFixed(1) + "%";
}

/* =====================================================================
   DATA LOADING
   ===================================================================== */

async function loadDataset(year = "australia_2023-24") {
  // Check for embedded dataset (works on file://)
  const datasets = window.__DATASETS__ || {};
  if (datasets[year]) {
    return datasets[year];
  }

  // Try fetch (works on http://)
  try {
    const url = `../data/processed/${year.replace("_", "/").replace("-", "/")}.json`;
    const resp = await fetch(`../data/processed/australia_2023-24.json`);
    if (resp.ok) return await resp.json();
  } catch (_) {}

  console.error("Dataset not found. Run: python pipeline/build_dataset.py");
  return null;
}

/* =====================================================================
   FILTER & SORT
   ===================================================================== */

function applyFilter(companies) {
  if (activeFilter === "all") return companies;
  return companies.filter(c => {
    const ind = (c.industry || "").toLowerCase();
    switch (activeFilter) {
      case "mining":    return ind.includes("mining");
      case "banking":   return ind.includes("finance") || ind.includes("insurance");
      case "retail":    return ind.includes("retail");
      case "tech":      return ind.includes("information") || ind.includes("media") || ind.includes("telecom");
      case "healthcare":return ind.includes("health");
      case "energy":    return ind.includes("electricity") || ind.includes("gas") || ind.includes("water");
      case "construction": return ind.includes("construction");
      case "transport": return ind.includes("transport");
    }
    return true;
  });
}

function applySort(companies) {
  const key = sortState.key;
  const dir = sortState.dir === "asc" ? 1 : -1;

  return [...companies].sort((a, b) => {
    let av, bv;
    const at = computeTotals(a);
    const bt = computeTotals(b);
    switch (key) {
      case "total_ttc":   av = at.total;      bv = bt.total;      break;
      case "corp_tax":    av = a.taxes_borne?.corporate_income_tax ?? 0;
                          bv = b.taxes_borne?.corporate_income_tax ?? 0; break;
      case "employees":   av = a.employment?.employees_au ?? 0;
                          bv = b.employment?.employees_au ?? 0; break;
      case "multiplier":  av = at.multiplier ?? 0; bv = bt.multiplier ?? 0; break;
      case "rev_per_emp": av = a.metrics?.revenue_per_employee_aud ?? 0;
                          bv = b.metrics?.revenue_per_employee_aud ?? 0; break;
      case "revenue":     av = a.ato_data?.total_income ?? 0;
                          bv = b.ato_data?.total_income ?? 0; break;
      default:            av = at.total; bv = bt.total;
    }
    return (av - bv) * dir;
  });
}

/* =====================================================================
   CHART 1 — STACKED BAR (tax components by company)
   ===================================================================== */

function buildBarChart() {
  const canvas = document.getElementById("chart-bar");
  if (!canvas) return;

  const display = applySort(filteredCompanies).slice(0, topN);

  const labels = display.map(c => c.company);
  const activeComps = TAX_COMPONENTS.filter(t => activeToggles.has(t.id));

  const datasets = activeComps.map(comp => ({
    label: comp.label,
    backgroundColor: comp.color,
    data: display.map(c => {
      let v = 0;
      if (comp.category === "taxes_borne") {
        v = c.taxes_borne?.[comp.id] ?? 0;
      } else {
        v = c.taxes_collected?.[comp.id] ?? 0;
      }
      return viewMode === "per_employee"
        ? (c.employment?.employees_au > 0 ? v / c.employment.employees_au : 0)
        : v;
    }),
  }));

  const scale = viewMode === "per_employee" ? 1 : 1e9;
  const yLabel = viewMode === "per_employee" ? "Tax per Employee (AUD)" : "Total Tax Contribution (AUD B)";

  if (charts.bar) charts.bar.destroy();
  charts.bar = new Chart(canvas, {
    type: "bar",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => {
              const v = ctx.parsed.y;
              if (viewMode === "per_employee") {
                return `  ${ctx.dataset.label}: $${Math.round(v).toLocaleString()}`;
              }
              return `  ${ctx.dataset.label}: ${fmtBillions(v * scale)}`;
            },
            footer: items => {
              const total = items.reduce((s, i) => s + i.parsed.y, 0);
              if (viewMode === "per_employee") {
                return `  Total: $${Math.round(total).toLocaleString()}`;
              }
              return `  Total TTC: ${fmtBillions(total * scale)}`;
            },
          },
        },
      },
      scales: {
        x: {
          stacked: true,
          ticks: {
            maxRotation: 45,
            font: { size: 11 },
            callback: (val, idx) => {
              const label = labels[idx] || "";
              return label.length > 18 ? label.substring(0, 16) + "…" : label;
            },
          },
          grid: { display: false },
        },
        y: {
          stacked: true,
          title: { display: true, text: yLabel, font: { size: 12 } },
          ticks: {
            callback: v => viewMode === "per_employee"
              ? "$" + (v / 1000).toFixed(0) + "K"
              : fmtBillions(v),
          },
          grid: { color: "rgba(0,0,0,0.05)" },
        },
      },
    },
  });
}

/* =====================================================================
   CHART 2 — SCATTER: Employment Multiplier
   ===================================================================== */

function buildScatterChart() {
  const canvas = document.getElementById("chart-scatter");
  if (!canvas) return;

  // Group by industry for coloring
  const byIndustry = {};
  for (const c of filteredCompanies) {
    const ind = c.industry || "Other";
    if (!byIndustry[ind]) byIndustry[ind] = [];
    byIndustry[ind].push(c);
  }

  const datasets = Object.entries(byIndustry).map(([ind, cos]) => ({
    label: ind.split(" ")[0],
    backgroundColor: industryColor(ind) + "aa",
    borderColor: industryColor(ind),
    borderWidth: 1.5,
    pointRadius: cos.map(c => {
      const rev = c.ato_data?.total_income ?? 0;
      return Math.max(5, Math.min(22, Math.sqrt(rev / 1e8)));
    }),
    pointHoverRadius: cos.map(c => {
      const rev = c.ato_data?.total_income ?? 0;
      return Math.max(7, Math.min(24, Math.sqrt(rev / 1e8)));
    }),
    data: cos.map(c => {
      const totals = computeTotals(c);
      return {
        x: c.employment?.employees_au ?? 0,
        y: totals.multiplier ?? 1,
        _company: c.company,
        _industry: c.industry,
        _employees: c.employment?.employees_au,
        _corpTax: c.taxes_borne?.corporate_income_tax,
        _totalTTC: totals.total,
        _revenue: c.ato_data?.total_income,
      };
    }),
  }));

  if (charts.scatter) charts.scatter.destroy();
  charts.scatter = new Chart(canvas, {
    type: "scatter",
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: items => items[0].raw._company || "",
            label: item => {
              const d = item.raw;
              return [
                `Industry: ${(d._industry || "").split(" ").slice(0,2).join(" ")}`,
                `AU Employees: ${(d._employees || 0).toLocaleString()}`,
                `Corp Tax: ${fmtBillions(d._corpTax)}`,
                `Total TTC: ${fmtBillions(d._totalTTC)}`,
                `Multiplier: ${d.y != null ? d.y.toFixed(2) + "×" : "—"}`,
                `Revenue: ${fmtBillions(d._revenue)}`,
              ];
            },
          },
        },
        annotation: {
          annotations: {
            line1: {
              type: "line",
              yMin: 1, yMax: 1,
              borderColor: "rgba(0,0,0,0.15)",
              borderWidth: 1,
              borderDash: [4, 4],
              label: { display: false },
            },
          },
        },
      },
      scales: {
        x: {
          type: "logarithmic",
          title: { display: true, text: "Australian Employees (log scale)", font: { size: 12 } },
          ticks: {
            callback: v => {
              if (v === 1000) return "1K";
              if (v === 10000) return "10K";
              if (v === 100000) return "100K";
              if (v === 200000) return "200K";
              return null;
            },
          },
          grid: { color: "rgba(0,0,0,0.05)" },
        },
        y: {
          title: { display: true, text: "Employment Tax Multiplier (Total TTC / Corp Tax)", font: { size: 12 } },
          min: 1,
          ticks: {
            callback: v => v.toFixed(1) + "×",
          },
          grid: { color: "rgba(0,0,0,0.05)" },
        },
      },
    },
  });
}

/* =====================================================================
   CHART 3 — Revenue per Employee vs Corp Tax Share
   ===================================================================== */

function buildWedgeChart() {
  const canvas = document.getElementById("chart-wedge");
  if (!canvas) return;

  const byIndustry = {};
  for (const c of filteredCompanies) {
    const ind = c.industry || "Other";
    if (!byIndustry[ind]) byIndustry[ind] = [];
    byIndustry[ind].push(c);
  }

  const datasets = Object.entries(byIndustry).map(([ind, cos]) => ({
    label: ind.split(" ")[0],
    backgroundColor: industryColor(ind) + "bb",
    borderColor: industryColor(ind),
    borderWidth: 1.5,
    pointRadius: cos.map(c => {
      const emps = c.employment?.employees_au ?? 0;
      return Math.max(5, Math.min(22, Math.sqrt(emps / 500)));
    }),
    data: cos.map(c => {
      const totals = computeTotals(c);
      const revPerEmp = c.metrics?.revenue_per_employee_aud ?? 0;
      const corpPct = totals.total > 0
        ? (c.taxes_borne?.corporate_income_tax ?? 0) / totals.total
        : 0;
      return {
        x: revPerEmp,
        y: corpPct * 100,
        _company: c.company,
        _industry: c.industry,
        _revPerEmp: revPerEmp,
        _corpPct: corpPct,
        _employees: c.employment?.employees_au,
        _totalTTC: totals.total,
      };
    }),
  }));

  if (charts.wedge) charts.wedge.destroy();
  charts.wedge = new Chart(canvas, {
    type: "scatter",
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: items => items[0].raw._company || "",
            label: item => {
              const d = item.raw;
              return [
                `Revenue/employee: $${Math.round(d._revPerEmp / 1000)}K`,
                `Corp tax as % of TTC: ${(d._corpPct * 100).toFixed(1)}%`,
                `AU Employees: ${(d._employees || 0).toLocaleString()}`,
                `Total TTC: ${fmtBillions(d._totalTTC)}`,
              ];
            },
          },
        },
      },
      scales: {
        x: {
          type: "logarithmic",
          title: { display: true, text: "Revenue per AU Employee (AUD, log scale)", font: { size: 12 } },
          ticks: {
            callback: v => {
              if (v === 100000)  return "$100K";
              if (v === 500000)  return "$500K";
              if (v === 1000000) return "$1M";
              if (v === 5000000) return "$5M";
              if (v === 10000000) return "$10M";
              return null;
            },
          },
          grid: { color: "rgba(0,0,0,0.05)" },
        },
        y: {
          title: { display: true, text: "Corporate Tax as % of Total Tax Contribution", font: { size: 12 } },
          min: 0,
          max: 100,
          ticks: { callback: v => v + "%" },
          grid: { color: "rgba(0,0,0,0.05)" },
        },
      },
    },
  });
}

/* =====================================================================
   CHART 4 — Who Captures Corporate Profits? Tax vs Shareholder Returns
   X: Total TTC   Y: Capital returned to shareholders (dividends + buybacks)
   Bubble size: AU employee count   Colour: industry
   Diagonal parity line: tax = shareholder returns
   ===================================================================== */

function buildTSRChart() {
  const canvas = document.getElementById("chart-tsr");
  if (!canvas) return;

  const byIndustry = {};
  for (const c of filteredCompanies) {
    const ind = c.industry || "Other";
    if (!byIndustry[ind]) byIndustry[ind] = [];
    byIndustry[ind].push(c);
  }

  // Determine axis range for parity line
  let maxVal = 0;
  for (const c of filteredCompanies) {
    const totals = computeTotals(c);
    const cr = getCapitalReturns(c);
    maxVal = Math.max(maxVal, totals.total, cr.total);
  }

  // Parity reference line (Y = X)
  const parityDataset = {
    type: "line",
    label: "Parity (Tax = Returns)",
    data: [{ x: 0, y: 0 }, { x: maxVal * 1.08, y: maxVal * 1.08 }],
    borderColor: "rgba(80,80,80,0.22)",
    borderDash: [8, 4],
    borderWidth: 1.5,
    pointRadius: 0,
    fill: false,
    tension: 0,
    order: 0,
  };

  const companyDatasets = Object.entries(byIndustry).map(([ind, cos]) => ({
    type: "scatter",
    label: ind.split(" ")[0],
    backgroundColor: industryColor(ind) + "aa",
    borderColor: industryColor(ind),
    borderWidth: 1.5,
    pointRadius: cos.map(c => {
      const emps = c.employment?.employees_au ?? 0;
      return Math.max(5, Math.min(22, Math.sqrt(emps / 500)));
    }),
    pointHoverRadius: cos.map(c => {
      const emps = c.employment?.employees_au ?? 0;
      return Math.max(7, Math.min(24, Math.sqrt(emps / 500)));
    }),
    order: 1,
    data: cos.map(c => {
      const totals = computeTotals(c);
      const cr = getCapitalReturns(c);
      const ratio = totals.total > 0 ? cr.total / totals.total : null;
      const corpTaxRatio = (c.taxes_borne?.corporate_income_tax ?? 0) > 0
        ? cr.total / (c.taxes_borne?.corporate_income_tax ?? 1)
        : null;
      return {
        x: totals.total,
        y: cr.total,
        _company: c.company,
        _industry: c.industry,
        _ttc: totals.total,
        _corpTax: c.taxes_borne?.corporate_income_tax,
        _dividends: cr.dividends,
        _buybacks: cr.buybacks,
        _capitalReturned: cr.total,
        _ratio: ratio,
        _corpTaxRatio: corpTaxRatio,
        _employees: c.employment?.employees_au,
      };
    }),
  }));

  if (charts.tsr) charts.tsr.destroy();
  charts.tsr = new Chart(canvas, {
    type: "scatter",
    data: { datasets: [parityDataset, ...companyDatasets] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "nearest", intersect: true },
      plugins: {
        legend: { display: false },
        tooltip: {
          filter: item => item.dataset.type !== "line",
          callbacks: {
            title: items => items[0].raw._company || "",
            label: item => {
              const d = item.raw;
              if (!d._company) return null;
              return [
                `Industry: ${(d._industry || "").split(" ").slice(0, 2).join(" ")}`,
                `Total TTC: ${fmtBillions(d._ttc)}`,
                `  of which corp tax: ${fmtBillions(d._corpTax)}`,
                `Dividends paid: ${fmtBillions(d._dividends)}`,
                `Buybacks: ${fmtBillions(d._buybacks)}`,
                `Capital returned: ${fmtBillions(d._capitalReturned)}`,
                `Returns ÷ TTC: ${d._ratio != null ? d._ratio.toFixed(2) + "×" : "—"}`,
                `Returns ÷ corp tax: ${d._corpTaxRatio != null ? d._corpTaxRatio.toFixed(2) + "×" : "—"}`,
                `AU Employees: ${(d._employees || 0).toLocaleString()}`,
              ];
            },
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: "Total Tax Contribution (TTC) — AUD", font: { size: 12 } },
          ticks: { callback: v => fmtBillions(v) },
          grid: { color: "rgba(0,0,0,0.05)" },
          min: 0,
        },
        y: {
          title: { display: true, text: "Capital Returned to Shareholders (Dividends + Buybacks) — AUD", font: { size: 12 } },
          ticks: { callback: v => fmtBillions(v) },
          grid: { color: "rgba(0,0,0,0.05)" },
          min: 0,
        },
      },
    },
  });
}

/* =====================================================================
   DATA TABLE
   ===================================================================== */

function buildTable() {
  const tbody = document.getElementById("table-body");
  if (!tbody) return;

  const sorted = applySort(filteredCompanies);
  const maxMult = Math.max(...sorted.map(c => computeTotals(c).multiplier ?? 0));

  tbody.innerHTML = "";

  for (const c of sorted) {
    const t = computeTotals(c);
    const isActual = c.ato_data?.is_ato_actual;
    const revPerEmp = c.metrics?.revenue_per_employee_aud;
    const empCount = c.employment?.employees_au;
    const barWidth = maxMult > 0 ? Math.min(100, ((t.multiplier ?? 0) / maxMult) * 100) : 0;

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="company-cell">
        <div class="company-name">${c.company}</div>
        <div class="company-industry">
          <span class="industry-pill ${industryClass(c.industry || "")}">${
            (c.industry || "Other").split(" ").slice(0, 2).join(" ")
          }</span>
        </div>
      </td>
      <td class="num">${empCount != null ? fmtNum(empCount) : "—"}</td>
      <td class="num">${fmtBillions(c.ato_data?.total_income)}</td>
      <td class="num num-highlight">
        ${fmtBillions(c.taxes_borne?.corporate_income_tax)}
        <div style="margin-top:2px">
          <span class="badge ${isActual ? "badge-actual" : "badge-est"}">${isActual ? "ATO" : "est"}</span>
        </div>
      </td>
      <td class="num">${fmtBillions(t.values.employer_payroll_tax)}</td>
      <td class="num">${fmtBillions((t.values.employee_income_tax_withheld ?? 0) + (t.values.employee_medicare_levy ?? 0))}</td>
      <td class="num">${fmtBillions(t.values.employee_gst_spending_estimate)}</td>
      <td class="num resource-cell">${
        c.resource_payments_to_crown?.is_applicable
          ? `<span title="Royalties: ${fmtBillions(c.resource_payments_to_crown.royalties)} · PRRT: ${fmtBillions(c.resource_payments_to_crown.prrt)}">${fmtBillions(c.resource_payments_to_crown.total)}</span>`
          : '<span class="text-muted">—</span>'
      }</td>
      <td class="num num-highlight">${fmtBillions(t.total)}</td>
      <td class="multiplier-cell">
        <div class="multiplier-bar-wrap">
          <div class="multiplier-bar" style="width:${barWidth}%"></div>
          <span class="multiplier-value">${t.multiplier != null ? t.multiplier.toFixed(2) + "×" : "—"}</span>
        </div>
      </td>
      <td class="num">${revPerEmp != null ? "$" + fmtNum(Math.round(revPerEmp / 1000)) + "K" : "—"}</td>
    `;
    tbody.appendChild(tr);
  }
}

/* =====================================================================
   KEY FINDINGS SUMMARY
   ===================================================================== */

function updateInsights() {
  const totals = filteredCompanies.map(c => computeTotals(c));
  const totalCorpTax = filteredCompanies.reduce(
    (s, c) => s + (c.taxes_borne?.corporate_income_tax ?? 0), 0
  );
  const totalTTC = totals.reduce((s, t) => s + t.total, 0);
  const totalEmp = filteredCompanies.reduce(
    (s, c) => s + (c.employment?.employees_au ?? 0), 0
  );
  const avgMult = totals.filter(t => t.multiplier).reduce((s, t) => s + t.multiplier, 0) /
    Math.max(1, totals.filter(t => t.multiplier).length);

  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  const totalCapitalReturns = filteredCompanies.reduce((s, c) => s + getCapitalReturns(c).total, 0);
  const tsrRatio = totalTTC > 0 ? totalCapitalReturns / totalTTC : null;

  set("insight-corp-tax",        fmtBillions(totalCorpTax));
  set("insight-total-ttc",       fmtBillions(totalTTC));
  set("insight-multiplier",      avgMult.toFixed(2) + "×");
  set("insight-employees",       fmtNum(totalEmp));
  set("insight-capital-returns", fmtBillions(totalCapitalReturns));
  set("insight-tsr-ratio",       tsrRatio != null ? tsrRatio.toFixed(2) + "×" : "—");
}

/* =====================================================================
   REFRESH — re-render everything after state change
   ===================================================================== */

function refresh() {
  filteredCompanies = applyFilter(allCompanies);
  updateInsights();
  buildBarChart();
  buildScatterChart();
  buildWedgeChart();
  buildTSRChart();
  buildTable();
  updateLegend();
}

/* =====================================================================
   LEGEND
   ===================================================================== */

function updateLegend() {
  const container = document.getElementById("chart-legend");
  if (!container) return;
  container.innerHTML = TAX_COMPONENTS.map(comp => {
    const active = activeToggles.has(comp.id);
    return `
      <div class="legend-item" style="opacity:${active ? 1 : 0.4}">
        <div class="legend-swatch" style="background:${comp.color}"></div>
        <span>${comp.label}</span>
        ${comp.tag === "actual"   ? '<span style="font-size:.65rem;color:#155724;font-weight:700"> ATO</span>' : ""}
        ${comp.tag === "rough"    ? '<span style="font-size:.65rem;color:#856404;font-weight:700"> rough</span>' : ""}
        ${comp.tag === "resource" ? '<span style="font-size:.65rem;color:#7b3f00;font-weight:700"> not a tax</span>' : ""}
      </div>`;
  }).join("");
}

/* =====================================================================
   SORT HEADER CLICK
   ===================================================================== */

function updateSortHeaders() {
  document.querySelectorAll(".data-table th[data-sort]").forEach(th => {
    const key = th.dataset.sort;
    th.classList.toggle("sorted", key === sortState.key);
    const arrow = th.querySelector(".sort-arrow");
    if (arrow) {
      arrow.textContent = key === sortState.key
        ? (sortState.dir === "desc" ? " ▼" : " ▲")
        : " ⇅";
    }
  });
}

/* =====================================================================
   CSV DOWNLOAD
   ===================================================================== */

function downloadCSV() {
  const headers = [
    "Company", "Industry", "State", "Employees (AU)",
    "Revenue (AUD)", "Corp Tax (AUD)", "Payroll Tax est (AUD)",
    "Employee Income Tax est (AUD)", "Medicare est (AUD)",
    "GST from Spending est (AUD)", "Land Tax est (AUD)",
    "Royalties paid to Crown (AUD)", "PRRT paid to Crown (AUD)",
    "Total TTC (AUD)", "Employment Multiplier", "Revenue per Employee (AUD)",
    "Corp Tax Source",
  ];

  const rows = [headers.join(",")];

  for (const c of applySort(filteredCompanies)) {
    const t = computeTotals(c);
    const row = [
      `"${c.company}"`,
      `"${c.industry}"`,
      c.primary_state,
      c.employment?.employees_au ?? "",
      c.ato_data?.total_income ?? "",
      c.taxes_borne?.corporate_income_tax ?? "",
      c.taxes_borne?.employer_payroll_tax ?? "",
      c.taxes_collected?.employee_income_tax_withheld ?? "",
      c.taxes_collected?.employee_medicare_levy ?? "",
      c.taxes_collected?.employee_gst_spending_estimate ?? "",
      c.taxes_borne?.land_tax_estimate ?? "",
      c.resource_payments_to_crown?.royalties ?? "",
      c.resource_payments_to_crown?.prrt ?? "",
      t.total,
      t.multiplier != null ? t.multiplier.toFixed(3) : "",
      c.metrics?.revenue_per_employee_aud ?? "",
      `"${c.ato_data?.data_source ?? "estimate"}"`,
    ];
    rows.push(row.join(","));
  }

  const blob = new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "corporate_tax_research_australia_2023-24.csv";
  link.click();
}

/* =====================================================================
   INIT
   ===================================================================== */

async function init() {
  // dataset_2023_24.js is loaded synchronously via <script> tag before app.js,
  // so window.__DATASETS__ is already populated — no spinner needed.
  const dataset = await loadDataset("australia_2023-24");

  if (!dataset) {
    const mainEl = document.getElementById("main-content");
    if (mainEl) mainEl.innerHTML = `
      <div class="container" style="padding:3rem 0">
        <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:2rem;max-width:600px">
          <h3 style="color:#856404;margin-bottom:0.5rem">Dataset not found</h3>
          <p style="color:#856404;margin:0">Run the pipeline to generate data:</p>
          <pre style="background:#fff;padding:0.75rem;margin-top:0.75rem;border-radius:4px;font-size:0.85rem">cd corporate-tax-research-2026
python pipeline/build_dataset.py</pre>
        </div>
      </div>`;
    return;
  }

  allCompanies = dataset.companies || [];

  // Update aggregate stats in the header
  const meta = dataset.aggregates || {};
  const setEl = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  setEl("agg-companies",  fmtNum(allCompanies.length));
  setEl("agg-corp-tax",   fmtBillions(meta.total_corporate_income_tax));
  setEl("agg-ttc",        fmtBillions(meta.total_tax_contribution_core));
  setEl("agg-employees",  fmtNum(meta.total_employees_au));

  // Wire up controls then render
  bindControls();
  refresh();
}

function bindControls() {
  // Tax toggles
  document.querySelectorAll(".tax-toggle input").forEach(input => {
    input.addEventListener("change", () => {
      const id = input.dataset.component;
      if (input.checked) activeToggles.add(id);
      else activeToggles.delete(id);
      refresh();
    });
  });

  // Sector filter
  const filterSel = document.getElementById("filter-sector");
  if (filterSel) filterSel.addEventListener("change", e => {
    activeFilter = e.target.value;
    filteredCompanies = applyFilter(allCompanies);
    refresh();
  });

  // Sort select
  const sortSel = document.getElementById("sort-by");
  if (sortSel) sortSel.addEventListener("change", e => {
    sortState.key = e.target.value;
    refresh();
    updateSortHeaders();
  });

  // Top-N slider
  const slider = document.getElementById("top-n-slider");
  if (slider) {
    slider.addEventListener("input", e => {
      topN = parseInt(e.target.value);
      const label = document.getElementById("top-n-label");
      if (label) label.textContent = topN;
      buildBarChart(); // only bar chart is limited by topN
    });
  }

  // View toggle (total / per employee)
  document.querySelectorAll(".view-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      viewMode = btn.dataset.view;
      document.querySelectorAll(".view-btn").forEach(b => b.classList.toggle("active", b === btn));
      buildBarChart();
    });
  });

  // Table sort headers
  document.querySelectorAll(".data-table th[data-sort]").forEach(th => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      if (sortState.key === key) {
        sortState.dir = sortState.dir === "desc" ? "asc" : "desc";
      } else {
        sortState.key = key;
        sortState.dir = "desc";
      }
      buildTable();
      updateSortHeaders();
    });
  });
  updateSortHeaders();

  // Download CSV
  const dlBtn = document.getElementById("download-csv");
  if (dlBtn) dlBtn.addEventListener("click", downloadCSV);

  // Methodology toggles
  document.querySelectorAll("[data-method-toggle]").forEach(btn => {
    btn.addEventListener("click", () => {
      const target = document.getElementById(btn.dataset.methodToggle);
      const isOpen = target?.classList.toggle("open");
      btn.textContent = isOpen ? "Hide methodology ▲" : "Show methodology ▼";
    });
  });

  // Main methodology banner
  const methToggle = document.getElementById("meth-toggle");
  const methContent = document.getElementById("meth-content");
  if (methToggle && methContent) {
    methToggle.addEventListener("click", () => {
      const isOpen = methContent.classList.toggle("open");
      methToggle.classList.toggle("open", isOpen);
    });
  }
}

document.addEventListener("DOMContentLoaded", init);
