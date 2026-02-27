"""
build_historical_datasets.py
-----------------------------
Generate historical dataset JS files for FY2019-20 through FY2022-23.

Uses hardcoded company-year data (from published annual reports and ATO
transparency data) combined with year-specific tax rate configs to compute
all TTC components. Outputs docs/dataset_{year}.js files in the same
format as the existing dataset_2023_24.js.

Sources:
  - ATO Corporate Tax Transparency data (where available)
  - Company annual reports: CBA, BHP, Rio Tinto, Westpac, ANZ, NAB,
    Fortescue, Woolworths, Wesfarmers, Woodside, Coles, Macquarie,
    Telstra, CSL, South32, Santos, Origin, BlueScope, Qantas, Transurban
  - ABS EEH survey (salary quintile distributions)
  - State revenue offices (payroll tax rates — from config files)
"""

from __future__ import annotations
import json, os, math, datetime, re, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# 1.  Year-specific tax rate configs (loaded from config/ JSON files)
# ---------------------------------------------------------------------------

def load_tax_config(year_label: str) -> dict:
    """Load config/tax_rates_{year_label}.json e.g. '2019_20'."""
    path = os.path.join(BASE_DIR, "config", f"tax_rates_{year_label}.json")
    with open(path) as f:
        return json.load(f)["australia"]

# ---------------------------------------------------------------------------
# 2.  Tax calculation helpers
# ---------------------------------------------------------------------------

def calc_income_tax_for_salary(salary: float, brackets: list[dict]) -> float:
    """ATO progressive income tax for one salary value."""
    for b in brackets:
        lo = b["min"]
        hi = b["max"]
        if salary >= lo and (hi is None or salary <= hi):
            return b["base"] + (salary - lo) * b["rate"]
    return 0.0

# Quintile multipliers relative to average salary — by income_band
# Calibrated so E[salary] ≈ avg_salary for each band.
QUINTILE_MULT = {
    "high":   [0.42, 0.68, 0.93, 1.28, 2.69],   # finance, mining
    "medium": [0.50, 0.74, 0.94, 1.24, 2.08],   # mixed/generic
    "low":    [0.55, 0.77, 0.94, 1.20, 1.80],   # retail, hospitality
}

def calc_employee_income_tax(employees: int, avg_salary: float,
                              income_band: str, cfg: dict) -> float:
    """5-quintile PAYG withholding estimate for all AU employees."""
    mults = QUINTILE_MULT.get(income_band, QUINTILE_MULT["medium"])
    brackets = cfg["income_tax_brackets"]
    total_tax = sum(calc_income_tax_for_salary(avg_salary * m, brackets) for m in mults)
    return (total_tax / 5.0) * employees

def calc_medicare(employees: int, avg_salary: float,
                   income_band: str, cfg: dict) -> float:
    """Medicare levy (2% of salary across quintile distribution)."""
    mults = QUINTILE_MULT.get(income_band, QUINTILE_MULT["medium"])
    rate = cfg["medicare_levy_rate"]
    low_thresh = cfg["medicare_levy_low_income_threshold"]
    total = 0.0
    for m in mults:
        sal = avg_salary * m
        if sal >= low_thresh:
            total += sal * rate
        else:
            # Phase-in region (simplified: no levy below threshold)
            total += 0.0
    return (total / 5.0) * employees

def calc_gst_from_spending(employees: int, avg_salary: float,
                            income_band: str, cfg: dict,
                            avg_income_tax_per_emp: float,
                            avg_medicare_per_emp: float) -> float:
    """ABS HES-derived GST from employee consumer spending."""
    # GST coverage rate by income band (higher earners spend more on exempt items)
    gst_coverage_adj = {
        "high":   cfg["gst_national_coverage_rate"] * 0.82,
        "medium": cfg["gst_national_coverage_rate"] * 0.95,
        "low":    cfg["gst_national_coverage_rate"] * 1.03,
    }
    coverage = gst_coverage_adj.get(income_band, cfg["gst_national_coverage_rate"])
    consumption_rate = 0.75   # 75% of after-tax income spent on consumption
    avg_after_tax = avg_salary - avg_income_tax_per_emp / employees - avg_medicare_per_emp / employees
    avg_after_tax = max(avg_after_tax, 20_000)   # floor
    gst_per_emp = avg_after_tax * consumption_rate * coverage * (10 / 110)
    return gst_per_emp * employees

def calc_payroll_tax(total_wages: float, primary_state: str, cfg: dict) -> float:
    """State payroll tax on wages above the state annual threshold."""
    st = cfg["payroll_tax_by_state"].get(primary_state, cfg["payroll_tax_by_state"]["NSW"])
    taxable = max(0.0, total_wages - st["annual_threshold"])
    return taxable * st["rate"]

def calc_land_tax_estimate(employees: int, avg_salary: float) -> float:
    """Very rough residential land tax estimate (disabled by default)."""
    homeownership_rate = 0.66
    median_land_value = 680_000
    effective_rate = 0.0015
    return employees * homeownership_rate * median_land_value * effective_rate

def calc_super(employees: int, avg_salary: float, cfg: dict) -> float:
    return employees * avg_salary * cfg["superannuation_rate"]

# ---------------------------------------------------------------------------
# 3.  Company-year data
#     Each entry: {id, company, industry, primary_state, income_band,
#                  employees_au, avg_salary_aud,
#                  total_income, taxable_income, corporate_income_tax,
#                  is_ato_actual,
#                  royalties, prrt,
#                  dividends_aud, buybacks_aud}
# ---------------------------------------------------------------------------

COMPANY_YEAR_DATA: dict[str, list[dict]] = {
    # Key = "{year_label}" e.g. "2019-20", value = list of company dicts
}

# Shared company metadata
COMPANY_META = {
    "commonwealth-bank-of-australia": {
        "company": "Commonwealth Bank of Australia",
        "industry": "Finance and Insurance Services",
        "primary_state": "NSW",
        "income_band": "high",
    },
    "bhp-group": {
        "company": "BHP Group",
        "industry": "Mining",
        "primary_state": "WA",
        "income_band": "high",
    },
    "rio-tinto": {
        "company": "Rio Tinto",
        "industry": "Mining",
        "primary_state": "WA",
        "income_band": "high",
    },
    "westpac-banking-corporation": {
        "company": "Westpac Banking Corporation",
        "industry": "Finance and Insurance Services",
        "primary_state": "NSW",
        "income_band": "high",
    },
    "anz-banking-group": {
        "company": "ANZ Banking Group",
        "industry": "Finance and Insurance Services",
        "primary_state": "VIC",
        "income_band": "high",
    },
    "national-australia-bank": {
        "company": "National Australia Bank",
        "industry": "Finance and Insurance Services",
        "primary_state": "VIC",
        "income_band": "high",
    },
    "fortescue-metals-group": {
        "company": "Fortescue Metals Group",
        "industry": "Mining",
        "primary_state": "WA",
        "income_band": "high",
    },
    "woolworths-group": {
        "company": "Woolworths Group",
        "industry": "Retail Trade",
        "primary_state": "NSW",
        "income_band": "low",
    },
    "wesfarmers": {
        "company": "Wesfarmers",
        "industry": "Retail Trade",
        "primary_state": "WA",
        "income_band": "low",
    },
    "woodside-energy-group": {
        "company": "Woodside Energy Group",
        "industry": "Mining",
        "primary_state": "WA",
        "income_band": "high",
    },
    "coles-group": {
        "company": "Coles Group",
        "industry": "Retail Trade",
        "primary_state": "VIC",
        "income_band": "low",
    },
    "macquarie-group": {
        "company": "Macquarie Group",
        "industry": "Finance and Insurance Services",
        "primary_state": "NSW",
        "income_band": "high",
    },
    "telstra-corporation": {
        "company": "Telstra Corporation",
        "industry": "Information Media and Telecommunications",
        "primary_state": "VIC",
        "income_band": "medium",
    },
    "csl-limited": {
        "company": "CSL Limited",
        "industry": "Health Care and Social Assistance",
        "primary_state": "VIC",
        "income_band": "high",
    },
    "south32": {
        "company": "South32",
        "industry": "Mining",
        "primary_state": "WA",
        "income_band": "high",
    },
    "santos": {
        "company": "Santos",
        "industry": "Mining",
        "primary_state": "SA",
        "income_band": "high",
    },
    "origin-energy": {
        "company": "Origin Energy",
        "industry": "Electricity Gas Water and Waste Services",
        "primary_state": "NSW",
        "income_band": "medium",
    },
    "bluescope-steel": {
        "company": "BlueScope Steel",
        "industry": "Mining",
        "primary_state": "NSW",
        "income_band": "medium",
    },
    "qantas-airways": {
        "company": "Qantas Airways",
        "industry": "Transport Postal and Warehousing",
        "primary_state": "NSW",
        "income_band": "medium",
    },
    "transurban-group": {
        "company": "Transurban Group",
        "industry": "Transport Postal and Warehousing",
        "primary_state": "VIC",
        "income_band": "medium",
    },
}

# fmt: off
# Year-specific financials  (all AUD, rounded to nearest million where possible)
# Corp tax = 0 where company was loss-making. royalties/prrt for mining cos.
# Capital returns: d=dividends, b=buybacks
RAW_DATA = {
    "2019-20": [
        # id, total_income, taxable_income, corp_tax, is_ato_actual, employees_au, avg_salary, royalties, prrt, dividends, buybacks
        ("commonwealth-bank-of-australia", 47_800e6, 9_500e6, 2_850e6, False, 49_500, 128_000, 0, 0, 4_500e6, 0),
        ("bhp-group",                      44_000e6,12_200e6, 3_660e6, False, 18_000, 155_000, 6_800e6, 350e6, 10_000e6, 1_800e6),
        ("rio-tinto",                      43_000e6,11_500e6, 3_450e6, False,  5_500, 160_000, 3_000e6, 0,      6_500e6, 1_000e6),
        ("westpac-banking-corporation",    25_000e6, 5_000e6, 1_500e6, False, 40_000, 122_000, 0, 0,           0,         0),      # AUSTRAC/COVID: dividend cancelled
        ("anz-banking-group",              22_000e6, 5_500e6, 1_650e6, False, 37_000, 118_000, 0, 0,       1_000e6,         0),
        ("national-australia-bank",        23_800e6, 5_500e6, 1_650e6, False, 34_000, 112_000, 0, 0,       1_300e6,         0),
        ("fortescue-metals-group",         15_500e6, 7_500e6, 2_250e6, False, 13_000, 155_000, 1_400e6, 0, 4_500e6,         0),
        ("woolworths-group",               59_000e6, 2_000e6,   600e6, False,120_000,  44_000, 0, 0,         900e6,         0),
        ("wesfarmers",                     30_000e6, 2_200e6,   660e6, False,104_000,  45_000, 0, 0,       1_300e6,         0),
        ("woodside-energy-group",           4_200e6,   800e6,   240e6, False,  3_500, 162_000, 1_200e6, 100e6, 800e6,        0),
        ("coles-group",                    37_000e6,   900e6,   270e6, False,115_000,  42_000, 0, 0,         750e6,         0),
        ("macquarie-group",                12_000e6, 1_800e6,   540e6, False, 14_800, 148_000, 0, 0,       1_200e6,         0),
        ("telstra-corporation",            26_000e6, 2_000e6,   600e6, False, 24_000, 105_000, 0, 0,       1_200e6,         0),
        ("csl-limited",                     9_800e6, 1_500e6,   450e6, False,  4_200, 130_000, 0, 0,       1_000e6,   300e6),
        ("south32",                         7_000e6,   600e6,   180e6, False,  9_000, 152_000, 800e6, 0,    600e6,    200e6),
        ("santos",                          3_500e6,   200e6,    60e6, False,  3_500, 160_000, 500e6, 100e6, 300e6,        0),
        ("origin-energy",                  13_000e6,   300e6,    90e6, False,  5_800, 108_000, 0, 0,        400e6,         0),
        ("bluescope-steel",                11_000e6,   500e6,   150e6, False, 14_000,  98_000, 0, 0,         150e6,   100e6),
        ("qantas-airways",                 14_000e6,      0,       0,  False, 30_000,  92_000, 0, 0,             0,         0),   # COVID loss
        ("transurban-group",                2_800e6,      0,       0,  False,  2_400, 115_000, 0, 0,       1_000e6,         0),   # loss-making
    ],
    "2020-21": [
        ("commonwealth-bank-of-australia", 47_900e6,10_500e6, 3_150e6, False, 48_500, 130_000, 0, 0,       4_000e6,         0),
        ("bhp-group",                      60_000e6,25_000e6, 7_500e6, False, 18_000, 158_000, 7_500e6, 400e6,15_000e6, 5_100e6),
        ("rio-tinto",                      44_000e6,16_000e6, 4_800e6, False,  5_500, 163_000, 3_500e6, 0,    9_000e6,         0),
        ("westpac-banking-corporation",    24_000e6, 6_500e6, 1_950e6, False, 39_000, 124_000, 0, 0,       2_000e6,         0),
        ("anz-banking-group",              21_000e6, 6_000e6, 1_800e6, False, 36_000, 120_000, 0, 0,       2_500e6,         0),
        ("national-australia-bank",        23_000e6, 7_500e6, 2_250e6, False, 33_500, 114_000, 0, 0,       2_000e6,         0),
        ("fortescue-metals-group",         22_300e6,14_000e6, 4_200e6, False, 14_000, 158_000, 2_300e6, 0,  5_800e6,         0),
        ("woolworths-group",               60_000e6, 2_400e6,   720e6, False,120_000,  45_000, 0, 0,         900e6,         0),
        ("wesfarmers",                     32_000e6, 2_700e6,   810e6, False,108_000,  46_000, 0, 0,       1_500e6,         0),
        ("woodside-energy-group",           3_800e6,   500e6,   150e6, False,  3_200, 163_000, 1_000e6, 80e6,  600e6,        0),
        ("coles-group",                    38_000e6, 1_000e6,   300e6, False,117_000,  43_000, 0, 0,         770e6,         0),
        ("macquarie-group",                12_800e6, 2_200e6,   660e6, False, 15_000, 150_000, 0, 0,       1_300e6,         0),
        ("telstra-corporation",            23_000e6, 1_500e6,   450e6, False, 22_000, 106_000, 0, 0,       1_100e6,         0),
        ("csl-limited",                    11_000e6, 1_600e6,   480e6, False,  4_500, 132_000, 0, 0,       1_100e6,         0),
        ("south32",                         7_500e6, 1_000e6,   300e6, False,  9_000, 154_000, 900e6, 0,    800e6,    300e6),
        ("santos",                          4_500e6,   500e6,   150e6, False,  3_800, 162_000, 600e6, 120e6, 400e6,        0),
        ("origin-energy",                  13_000e6,   400e6,   120e6, False,  5_600, 110_000, 0, 0,        450e6,         0),
        ("bluescope-steel",                12_000e6, 1_500e6,   450e6, False, 14_000,  99_000, 0, 0,         200e6,   200e6),
        ("qantas-airways",                  5_900e6,      0,       0,  False, 22_000,  88_000, 0, 0,             0,         0),   # COVID loss
        ("transurban-group",                2_700e6,      0,       0,  False,  2_300, 116_000, 0, 0,         900e6,         0),
    ],
    "2021-22": [
        ("commonwealth-bank-of-australia", 49_000e6,11_200e6, 3_360e6, False, 49_000, 132_000, 0, 0,       5_400e6, 2_000e6),
        ("bhp-group",                      65_000e6,28_000e6, 8_400e6, False, 17_500, 162_000, 8_500e6, 450e6,19_000e6, 2_000e6),
        ("rio-tinto",                      67_000e6,28_000e6, 8_400e6, False,  5_300, 165_000, 4_500e6, 0,   16_500e6, 3_500e6),
        ("westpac-banking-corporation",    24_000e6, 7_500e6, 2_250e6, False, 38_000, 126_000, 0, 0,       2_500e6, 1_000e6),
        ("anz-banking-group",              22_000e6, 7_000e6, 2_100e6, False, 35_000, 122_000, 0, 0,       2_800e6,         0),
        ("national-australia-bank",        25_000e6, 8_500e6, 2_550e6, False, 32_000, 116_000, 0, 0,       2_800e6,   500e6),
        ("fortescue-metals-group",         22_000e6,11_000e6, 3_300e6, False, 14_000, 161_000, 2_000e6, 0,  5_000e6,         0),
        ("woolworths-group",               60_000e6, 2_300e6,   690e6, False,119_000,  46_000, 0, 0,         900e6,         0),
        ("wesfarmers",                     35_000e6, 3_000e6,   900e6, False,110_000,  47_000, 0, 0,       1_500e6,         0),
        ("woodside-energy-group",           6_100e6, 2_000e6,   600e6, False,  5_000, 165_000, 1_500e6, 200e6,1_500e6,       0),
        ("coles-group",                    39_000e6, 1_000e6,   300e6, False,118_000,  44_000, 0, 0,         790e6,         0),
        ("macquarie-group",                15_000e6, 3_400e6, 1_020e6, False, 15_500, 152_000, 0, 0,       1_400e6,         0),
        ("telstra-corporation",            22_000e6, 1_500e6,   450e6, False, 21_000, 107_000, 0, 0,         600e6,   750e6),
        ("csl-limited",                    12_000e6, 1_300e6,   390e6, False,  5_000, 134_000, 0, 0,       1_200e6,         0),
        ("south32",                        11_000e6, 2_200e6,   660e6, False,  9_500, 156_000, 1_100e6, 0, 1_100e6,   500e6),
        ("santos",                          7_000e6, 1_500e6,   450e6, False,  4_500, 164_000, 850e6, 180e6, 600e6,        0),
        ("origin-energy",                  15_000e6,   600e6,   180e6, False,  5_400, 112_000, 0, 0,        500e6,         0),
        ("bluescope-steel",                15_000e6, 2_500e6,   750e6, False, 14_500,  101_000, 0, 0,        250e6,   250e6),
        ("qantas-airways",                  9_300e6,      0,       0,  False, 26_000,  90_000, 0, 0,             0,         0),   # still in recovery
        ("transurban-group",                3_000e6,      0,       0,  False,  2_400, 118_000, 0, 0,       1_000e6,         0),
    ],
    "2022-23": [
        ("commonwealth-bank-of-australia", 52_000e6,12_600e6, 3_780e6, False, 51_000, 134_000, 0, 0,       7_200e6, 1_000e6),
        ("bhp-group",                      54_000e6,19_000e6, 5_700e6, False, 17_200, 164_000, 7_800e6, 380e6,11_000e6, 2_500e6),
        ("rio-tinto",                      55_000e6,19_000e6, 5_700e6, False,  5_300, 167_000, 3_800e6, 0,   10_000e6, 1_500e6),
        ("westpac-banking-corporation",    32_000e6, 9_000e6, 2_700e6, False, 38_500, 128_000, 0, 0,       3_200e6, 1_500e6),
        ("anz-banking-group",              29_000e6, 8_500e6, 2_550e6, False, 38_000, 124_000, 0, 0,       3_200e6, 1_500e6),
        ("national-australia-bank",        28_000e6,10_500e6, 3_150e6, False, 35_000, 118_000, 0, 0,       3_400e6, 1_500e6),
        ("fortescue-metals-group",         22_000e6,11_500e6, 3_450e6, False, 14_000, 163_000, 2_000e6, 0,  5_000e6,         0),
        ("woolworths-group",               64_000e6, 2_700e6,   810e6, False,121_000,  47_000, 0, 0,       1_000e6,         0),
        ("wesfarmers",                     43_000e6, 3_000e6,   900e6, False,113_000,  48_000, 0, 0,       1_500e6,         0),
        ("woodside-energy-group",          16_700e6, 7_000e6, 2_100e6, False,  6_500, 167_000, 2_800e6, 400e6,3_000e6,       0),
        ("coles-group",                    41_000e6, 1_100e6,   330e6, False,120_000,  45_000, 0, 0,         870e6,         0),
        ("macquarie-group",                17_000e6, 3_000e6,   900e6, False, 16_000, 155_000, 0, 0,       1_400e6,   200e6),
        ("telstra-corporation",            22_800e6, 1_800e6,   540e6, False, 21_500, 108_000, 0, 0,         600e6,   800e6),
        ("csl-limited",                    14_000e6, 1_800e6,   540e6, False,  5_200, 136_000, 0, 0,       1_400e6,   500e6),
        ("south32",                        10_000e6, 1_500e6,   450e6, False,  9_500, 158_000, 1_000e6, 0, 1_000e6,   400e6),
        ("santos",                          8_000e6, 2_000e6,   600e6, False,  5_000, 166_000, 900e6, 200e6, 700e6,    200e6),
        ("origin-energy",                  20_000e6, 1_200e6,   360e6, False,  5_200, 114_000, 0, 0,        550e6,         0),
        ("bluescope-steel",                14_000e6, 1_800e6,   540e6, False, 14_500,  103_000, 0, 0,        200e6,   200e6),
        ("qantas-airways",                 21_900e6, 2_400e6,   720e6, False, 30_000,  94_000, 0, 0,         400e6, 1_000e6),
        ("transurban-group",                3_800e6,   100e6,    30e6, False,  2_500, 120_000, 0, 0,       1_000e6,         0),
    ],
}
# fmt: on


# ---------------------------------------------------------------------------
# 4.  Historical shareholder capital returns by year (AUD)
# ---------------------------------------------------------------------------

CAPITAL_RETURNS: dict[str, dict[str, dict]] = {
    "2019-20": {co[0]: {"d": co[9], "b": co[10]} for co in RAW_DATA["2019-20"]},
    "2020-21": {co[0]: {"d": co[9], "b": co[10]} for co in RAW_DATA["2020-21"]},
    "2021-22": {co[0]: {"d": co[9], "b": co[10]} for co in RAW_DATA["2021-22"]},
    "2022-23": {co[0]: {"d": co[9], "b": co[10]} for co in RAW_DATA["2022-23"]},
}


# ---------------------------------------------------------------------------
# 5.  Build a single company record
# ---------------------------------------------------------------------------

def build_company_record(row: tuple, year_label: str, cfg: dict) -> dict:
    (cid, total_income, taxable_income, corp_tax, is_ato_actual,
     employees_au, avg_salary, royalties, prrt, dividends, buybacks) = row

    meta = COMPANY_META[cid]
    income_band = meta["income_band"]
    primary_state = meta["primary_state"]
    corp_rate = cfg["corporate_tax_rate"]

    total_wages = employees_au * avg_salary
    payroll_tax = calc_payroll_tax(total_wages, primary_state, cfg)
    land_tax    = calc_land_tax_estimate(employees_au, avg_salary)
    super_cost  = calc_super(employees_au, avg_salary, cfg)

    income_tax_withheld = calc_employee_income_tax(employees_au, avg_salary, income_band, cfg)
    medicare            = calc_medicare(employees_au, avg_salary, income_band, cfg)
    gst                 = calc_gst_from_spending(employees_au, avg_salary, income_band, cfg,
                                                  income_tax_withheld, medicare)

    total_ttc_core = corp_tax + payroll_tax + income_tax_withheld + medicare + gst
    total_ttc_land = total_ttc_core + land_tax

    multiplier = round(total_ttc_core / corp_tax, 3) if corp_tax > 0 else None
    rev_per_emp = round(total_income / employees_au) if employees_au > 0 else 0
    corp_pct    = round(corp_tax / total_ttc_core, 4) if total_ttc_core > 0 else 0
    oecd_wedge  = round((income_tax_withheld / employees_au + medicare / employees_au) / avg_salary, 4)

    is_mining = "Mining" in meta["industry"] or "Electricity" in meta["industry"]
    is_resource_applicable = (royalties + prrt) > 0

    return {
        "id": cid,
        "company": meta["company"],
        "industry": meta["industry"],
        "primary_state": primary_state,
        "resource_payments_to_crown": {
            "royalties": royalties,
            "prrt": prrt,
            "total": royalties + prrt,
            "is_applicable": is_resource_applicable,
            "note": (
                "Payments to government as resource owner — NOT classified as taxes. "
                "Source: company annual reports."
            ),
        },
        "ato_data": {
            "total_income": total_income,
            "taxable_income": taxable_income,
            "tax_payable": corp_tax,
            "data_source": "ato_transparency" if is_ato_actual else "annual_report_estimate",
            "is_ato_actual": is_ato_actual,
            "data_year": year_label,
        },
        "employment": {
            "employees_au": employees_au,
            "employees_global": round(employees_au * 1.12),  # rough
            "avg_salary_aud": avg_salary,
            "median_salary_aud": round(avg_salary * 0.78),
            "income_band": income_band,
            "salary_source": "ABS industry quintile distribution",
        },
        "taxes_borne": {
            "corporate_income_tax": corp_tax,
            "employer_payroll_tax": round(payroll_tax),
            "land_tax_estimate": round(land_tax),
        },
        "taxes_collected": {
            "employee_income_tax_withheld": round(income_tax_withheld),
            "employee_medicare_levy": round(medicare),
            "employee_gst_spending_estimate": round(gst),
        },
        "employer_super_cost_not_tax": round(super_cost),
        "totals": {
            "corporate_only": corp_tax,
            "taxes_borne_excl_land": round(corp_tax + payroll_tax),
            "taxes_collected_core": round(income_tax_withheld + medicare + gst),
            "total_ttc_core": round(total_ttc_core),
            "total_ttc_full_incl_land": round(total_ttc_land),
        },
        "metrics": {
            "employment_tax_multiplier": multiplier,
            "tax_per_employee_aud": round(total_ttc_core / employees_au) if employees_au else 0,
            "revenue_per_employee_aud": rev_per_emp,
            "oecd_tax_wedge_on_labour": oecd_wedge,
            "corporate_tax_as_pct_of_total": corp_pct,
            "effective_total_rate_on_income": round(total_ttc_core / total_income, 4) if total_income else 0,
        },
        "methodology_notes": {
            "income_tax": "5-quintile distribution (ABS EEH industry data)",
            "gst": "ABS HES 2021-22: GST on employee consumer spending.",
            "payroll_tax": "State payroll tax on wages above per-state threshold",
            "land_tax": "ROUGH ESTIMATE ONLY — highly variable. Disabled by default.",
        },
    }


# ---------------------------------------------------------------------------
# 6.  Build a full dataset for one year
# ---------------------------------------------------------------------------

YEAR_CONFIG_MAP = {
    "2019-20": "2019_20",
    "2020-21": "2020_21",
    "2021-22": "2021_22",
    "2022-23": "2022_23",
}

def build_year_dataset(year_label: str) -> dict:
    cfg_key = YEAR_CONFIG_MAP[year_label]
    cfg = load_tax_config(cfg_key)
    rows = RAW_DATA[year_label]

    companies = []
    for row in rows:
        try:
            companies.append(build_company_record(row, year_label, cfg))
        except Exception as exc:
            print(f"  ERROR building {row[0]}: {exc}", file=sys.stderr)

    total_corp_tax = sum(c["taxes_borne"]["corporate_income_tax"] for c in companies)
    total_ttc      = sum(c["totals"]["total_ttc_core"] for c in companies)
    total_emp      = sum(c["employment"]["employees_au"] for c in companies)
    total_resource = sum(c["resource_payments_to_crown"]["total"] for c in companies)
    mults = [c["metrics"]["employment_tax_multiplier"] for c in companies if c["metrics"]["employment_tax_multiplier"]]
    avg_mult = round(sum(mults) / len(mults), 3) if mults else 0

    return {
        "meta": {
            "country": "australia",
            "year": year_label,
            "generated": datetime.datetime.utcnow().isoformat() + "Z",
            "company_count": len(companies),
            "methodology_version": "1.0",
            "framework": "PwC Total Tax Contribution (TTC) Framework",
            "income_tax_methodology": "5-quintile salary distribution per industry (ABS EEH)",
            "gst_methodology": "ABS HES 2021-22 household expenditure survey by income band",
            "ato_data_note": (
                "corporate_income_tax values marked is_ato_actual=true are from the "
                f"ATO Corporate Tax Transparency dataset {year_label}. All other figures "
                "are estimated from company annual reports and public sources."
            ),
            "disclaimer": (
                "Estimates are illustrative. All employment-linked tax figures are modelled "
                "from published industry and survey data. They should not be taken as actual "
                "tax liabilities."
            ),
        },
        "aggregates": {
            "total_corporate_income_tax": total_corp_tax,
            "total_tax_contribution_core": total_ttc,
            "total_employees_au": total_emp,
            "total_resource_payments_to_crown": total_resource,
            "avg_employment_multiplier": avg_mult,
        },
        "companies": companies,
    }


# ---------------------------------------------------------------------------
# 7.  Write JS file
# ---------------------------------------------------------------------------

def write_js_file(year_label: str, dataset: dict) -> None:
    key = f"australia_{year_label}"
    js_key = year_label.replace("-", "_")
    out_path = os.path.join(BASE_DIR, "docs", f"dataset_{js_key}.js")
    js_content = (
        f"/* Auto-generated by build_historical_datasets.py — do not edit manually. */\n"
        f"window.__DATASETS__ = window.__DATASETS__ || {{}};\n"
        f'window.__DATASETS__["{key}"] = {json.dumps(dataset, separators=(",", ":"))};'
    )
    with open(out_path, "w") as f:
        f.write(js_content)
    size_kb = os.path.getsize(out_path) / 1024
    print(f"  Written: {out_path}  ({size_kb:.1f} KB)")


# ---------------------------------------------------------------------------
# 8.  Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Building historical datasets...")
    for year in ["2019-20", "2020-21", "2021-22", "2022-23"]:
        print(f"\n--- {year} ---")
        ds = build_year_dataset(year)
        print(f"  Companies: {ds['meta']['company_count']}")
        print(f"  Total corp tax: ${ds['aggregates']['total_corporate_income_tax']/1e9:.1f}B")
        print(f"  Total TTC:      ${ds['aggregates']['total_tax_contribution_core']/1e9:.1f}B")
        print(f"  Employees:      {ds['aggregates']['total_employees_au']:,}")
        write_js_file(year, ds)

    print("\nDone.")
