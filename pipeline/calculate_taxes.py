"""
calculate_taxes.py
------------------
Core tax estimation functions for the Corporate Tax Research project.

Framework: Based on PwC Total Tax Contribution (TTC) Framework, which distinguishes:
  - Taxes Borne: paid directly by the company (corporate income tax, payroll tax, land tax)
  - Taxes Collected: collected on government's behalf (PAYG withholding, GST from employees)

Income tax methodology: Uses a 5-quintile salary distribution per industry rather than
just the median, correcting for Jensen's inequality (the convexity of progressive tax
means E[tax(salary)] > tax(E[salary])). Based on ABS Employee Earnings, Hours and
Leave Survey (EEH) 2023-24.

GST methodology: Based on ABS Household Expenditure Survey 2021-22. GST covers ~47%
of Australian household consumption nationally; rate varies by income band.

All estimates are clearly flagged in the output JSON.
"""

from __future__ import annotations
from typing import Optional
import json
import os


def load_config(config_dir: str = None) -> dict:
    """Load tax rates and reference data from config files."""
    if config_dir is None:
        config_dir = os.path.join(os.path.dirname(__file__), "..", "config")
    with open(os.path.join(config_dir, "tax_rates.json")) as f:
        tax_rates = json.load(f)
    return tax_rates


def load_reference_data(data_dir: str = None) -> dict:
    """Load industry salary and GST consumption reference data."""
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "reference")
    with open(os.path.join(data_dir, "industry_salaries.json")) as f:
        industry_salaries = json.load(f)
    with open(os.path.join(data_dir, "gst_consumption.json")) as f:
        gst_consumption = json.load(f)
    return {"industry_salaries": industry_salaries, "gst_consumption": gst_consumption}


def calculate_income_tax_for_salary(
    salary: float,
    brackets: list[dict],
    medicare_rate: float,
    medicare_low_income_threshold: float = 26000,
) -> dict:
    """
    Calculate Australian income tax and Medicare levy for a single salary level.

    Args:
        salary: Annual gross salary in AUD
        brackets: List of bracket dicts from tax_rates.json
        medicare_rate: Medicare levy rate (0.02)
        medicare_low_income_threshold: Below this, reduced/no Medicare levy

    Returns:
        dict with keys: income_tax, medicare_levy, total, effective_rate, marginal_rate
    """
    if salary <= 0:
        return {
            "income_tax": 0,
            "medicare_levy": 0,
            "total": 0,
            "effective_rate": 0,
            "marginal_rate": 0,
        }

    income_tax = 0.0
    marginal_rate = 0.0

    for bracket in brackets:
        b_min = bracket["min"]
        b_max = bracket["max"]
        rate = bracket["rate"]
        base = bracket["base"]

        if salary <= b_min:
            break

        if b_max is None or salary <= b_max:
            # Income falls within this bracket
            income_tax = base + (salary - b_min) * rate
            marginal_rate = rate
            break

    # Medicare levy (reduced phase-in for low incomes, simplified here)
    if salary <= medicare_low_income_threshold:
        medicare_levy = 0.0
    else:
        medicare_levy = salary * medicare_rate

    total = income_tax + medicare_levy
    effective_rate = total / salary if salary > 0 else 0

    return {
        "income_tax": round(income_tax),
        "medicare_levy": round(medicare_levy),
        "total": round(total),
        "effective_rate": round(effective_rate, 4),
        "marginal_rate": marginal_rate,
    }


def calculate_income_tax_quintile_distribution(
    industry_data: dict,
    brackets: list[dict],
    medicare_rate: float,
    employee_count: int,
    avg_salary_override: Optional[float] = None,
) -> dict:
    """
    Calculate employee income tax using a 5-quintile salary distribution.

    This corrects for Jensen's inequality: because the tax function is convex
    (marginal rates increase), using only the median salary UNDERSTATES the
    expected income tax. This matters especially for high-dispersion industries
    (mining: ~26% underestimate; finance: ~19% underestimate).

    Each quintile represents 20% of employees. We calculate tax for each quintile's
    representative salary and take the average.

    If avg_salary_override is provided, we scale the quintile distribution
    proportionally so the median aligns with the override.

    Returns:
        dict with per-employee and total estimates
    """
    quintiles = industry_data.get("salary_quintiles", [])
    median_annual = industry_data.get("median_annual", 75000)

    # If an override is provided, scale all quintiles proportionally
    if avg_salary_override and avg_salary_override > 0 and median_annual > 0:
        scale_factor = avg_salary_override / median_annual
        quintiles = [q * scale_factor for q in quintiles]
        median_annual = avg_salary_override

    if not quintiles:
        # Fallback: use median only (less accurate)
        quintiles = [median_annual]

    # Calculate tax for each quintile (equal 20% weight)
    weight = 1.0 / len(quintiles)
    total_weighted_tax = 0.0
    total_weighted_medicare = 0.0
    quintile_details = []

    for i, q_salary in enumerate(quintiles):
        result = calculate_income_tax_for_salary(
            q_salary, brackets, medicare_rate
        )
        total_weighted_tax += weight * result["income_tax"]
        total_weighted_medicare += weight * result["medicare_levy"]
        quintile_details.append(
            {
                "quintile": i + 1,
                "salary": round(q_salary),
                "income_tax": result["income_tax"],
                "medicare_levy": result["medicare_levy"],
                "effective_rate": result["effective_rate"],
            }
        )

    avg_income_tax_per_employee = round(total_weighted_tax)
    avg_medicare_per_employee = round(total_weighted_medicare)
    avg_salary = sum(quintiles) / len(quintiles)

    return {
        "avg_income_tax_per_employee": avg_income_tax_per_employee,
        "avg_medicare_per_employee": avg_medicare_per_employee,
        "avg_salary_used": round(avg_salary),
        "median_salary": round(median_annual),
        "total_income_tax": round(avg_income_tax_per_employee * employee_count),
        "total_medicare": round(avg_medicare_per_employee * employee_count),
        "quintile_details": quintile_details,
        "methodology": "5-quintile distribution (ABS EEH industry data)",
    }


def calculate_payroll_tax(
    employee_count: int,
    avg_salary: float,
    state_distribution: dict[str, float],
    payroll_tax_config: dict[str, dict],
) -> dict:
    """
    Calculate employer payroll tax across multiple states.

    For large national employers, employees are distributed across states.
    Each state's payroll tax applies on wages above the state threshold.

    Args:
        employee_count: Total Australian employees
        avg_salary: Average salary (used as proxy; actual is the quintile-weighted avg)
        state_distribution: dict mapping state code to proportion, e.g. {"NSW": 0.5, "VIC": 0.3}
        payroll_tax_config: State payroll tax rates and thresholds

    Returns:
        dict with total payroll tax and breakdown by state
    """
    total_wages = employee_count * avg_salary
    total_payroll_tax = 0.0
    breakdown = {}

    for state, proportion in state_distribution.items():
        state_config = payroll_tax_config.get(state)
        if not state_config:
            continue

        state_wages = total_wages * proportion
        threshold = state_config["annual_threshold"]
        rate = state_config["rate"]

        # Payroll tax applies on wages above the threshold per entity.
        # For large national employers, the entity's Australian payroll
        # in each state is well above threshold, so effectively all wages
        # in that state are taxed (above threshold is the small deductible portion).
        taxable_wages = max(0, state_wages - threshold)
        state_payroll_tax = taxable_wages * rate

        total_payroll_tax += state_payroll_tax
        breakdown[state] = {
            "employees_est": round(employee_count * proportion),
            "state_wages": round(state_wages),
            "taxable_wages": round(taxable_wages),
            "rate": rate,
            "payroll_tax": round(state_payroll_tax),
        }

    return {
        "total_payroll_tax": round(total_payroll_tax),
        "breakdown_by_state": breakdown,
        "methodology": "State payroll tax on wages above per-state threshold",
    }


def calculate_gst_estimate(
    employee_count: int,
    income_band: str,
    avg_after_tax_income: float,
    gst_consumption_config: dict,
    gst_rate: float = 0.10,
) -> dict:
    """
    Estimate GST generated from employees' consumer spending.

    Based on ABS Household Expenditure Survey 2021-22:
    - GST covers approximately 47% of Australian household consumption nationally
    - Low-income households spend proportionally more of income but less on GST-taxable goods
    - High-income households save more and spend proportionally more on GST-exempt categories
      (private health, financial services, overseas travel, private school fees)

    Formula:
        gst_per_employee = after_tax_income × consumption_rate × gst_coverage × (rate / (1+rate))
    Note: dividing by (1+rate) converts from GST-inclusive to GST-exclusive to get the tax portion.

    Args:
        employee_count: Number of employees
        income_band: 'low', 'low_mid', 'mid', 'mid_high', or 'high'
        avg_after_tax_income: Average after-tax income per employee
        gst_consumption_config: GST consumption parameters by income band
        gst_rate: GST rate (0.10 for Australia)

    Returns:
        dict with per-employee and total GST estimates
    """
    band_config = gst_consumption_config.get(
        income_band, gst_consumption_config.get("mid", {})
    )
    # Filter out metadata keys
    if "_" in income_band or not isinstance(band_config, dict):
        band_config = gst_consumption_config.get("mid", {})

    consumption_rate = band_config.get("consumption_rate", 0.85)
    gst_coverage = band_config.get("gst_coverage", 0.44)

    # GST is 1/11th of the GST-inclusive price (i.e., 10/110)
    gst_fraction = gst_rate / (1 + gst_rate)

    gst_per_employee = avg_after_tax_income * consumption_rate * gst_coverage * gst_fraction
    total_gst = gst_per_employee * employee_count

    return {
        "gst_per_employee": round(gst_per_employee),
        "total_gst_estimate": round(total_gst),
        "consumption_rate_used": consumption_rate,
        "gst_coverage_rate_used": gst_coverage,
        "income_band": income_band,
        "methodology": (
            "ABS HES 2021-22: GST on employee consumer spending. "
            f"Assumes {consumption_rate*100:.0f}% of after-tax income spent, "
            f"{gst_coverage*100:.0f}% of that spending is GST-taxable."
        ),
    }


def calculate_land_tax_estimate(
    employee_count: int,
    income_band: str,
    land_tax_config: dict,
) -> dict:
    """
    Rough estimate of land/council rates paid by employees as property owners.

    This is a very rough estimate and is clearly flagged as such.
    Based on: homeownership rate by income band × median residential land value × effective rate.

    This should be treated as indicative only — actual rates vary enormously by
    location, property type and individual circumstances.

    Returns:
        dict with estimate and prominent rough-estimate warning
    """
    homeownership_rates = land_tax_config.get(
        "homeownership_rate_by_income_band", {}
    )
    homeownership_rate = homeownership_rates.get(income_band, 0.60)
    median_land_value = land_tax_config.get("median_residential_land_value_aud", 600000)
    effective_rate = land_tax_config.get("effective_rate_residential", 0.005)

    land_tax_per_homeowner = median_land_value * effective_rate
    land_tax_per_employee = homeownership_rate * land_tax_per_homeowner
    total_land_tax = land_tax_per_employee * employee_count

    return {
        "land_tax_per_employee_est": round(land_tax_per_employee),
        "total_land_tax_estimate": round(total_land_tax),
        "homeownership_rate_used": homeownership_rate,
        "warning": "ROUGH ESTIMATE ONLY — highly variable by location and individual. Disabled by default.",
        "methodology": (
            f"Homeownership rate ({homeownership_rate*100:.0f}%) × "
            f"median land value (${median_land_value:,}) × "
            f"effective rate ({effective_rate*100:.2f}%)"
        ),
    }


def calculate_employer_super(
    employee_count: int,
    avg_salary: float,
    super_rate: float,
) -> dict:
    """
    Calculate mandatory employer superannuation contributions.

    Note: Superannuation is NOT a tax — it is deferred compensation paid into
    retirement accounts. However it represents a significant mandatory employer
    cost (11.5% from July 2024, rising to 12% from July 2025).

    Shown separately in the UI as an optional overlay, never included in
    tax totals by default.
    """
    per_employee = avg_salary * super_rate
    total = per_employee * employee_count

    return {
        "super_per_employee": round(per_employee),
        "total_super_cost": round(total),
        "super_rate": super_rate,
        "note": "Mandatory employer cost but NOT a tax. Shown separately as employer labour cost context.",
    }


def parse_state_distribution(state_distribution_str: str) -> dict[str, float]:
    """
    Parse a state distribution string like 'NSW:35;VIC:25;QLD:15;WA:10;SA:15'
    into a dict of proportions summing to 1.0.

    e.g. "NSW:50;VIC:30;QLD:20" → {"NSW": 0.5, "VIC": 0.3, "QLD": 0.2}
    """
    if not state_distribution_str or str(state_distribution_str).lower() == "nan":
        return {"NSW": 0.5, "VIC": 0.3, "QLD": 0.2}

    parts = str(state_distribution_str).split(";")
    raw = {}
    for part in parts:
        if ":" in part:
            state, pct = part.split(":", 1)
            state = state.strip().upper()
            # Only include states with known payroll tax (exclude overseas, NZ, etc.)
            valid_states = {"NSW", "VIC", "QLD", "WA", "SA", "ACT", "NT", "TAS"}
            if state in valid_states:
                raw[state] = float(pct.strip())

    total = sum(raw.values())
    if total == 0:
        return {"NSW": 0.5, "VIC": 0.3, "QLD": 0.2}

    return {k: v / total for k, v in raw.items()}


def get_industry_data(industry: str, reference_data: dict) -> dict:
    """
    Look up industry salary data, with fuzzy fallback matching.
    Returns the industry data dict or a default mid-range fallback.
    """
    salaries = reference_data["industry_salaries"]
    industry_keys = {k: k for k in salaries.keys() if not k.startswith("_")}

    # Direct match
    if industry in industry_keys:
        return salaries[industry]

    # Partial/fuzzy match
    industry_lower = industry.lower()
    for key in industry_keys:
        key_lower = key.lower()
        # Match key fragments
        if any(word in key_lower for word in industry_lower.split() if len(word) > 3):
            return salaries[key]

    # Fallback: use mid-range "Health Care and Social Assistance" as representative default
    return salaries.get(
        "Health Care and Social Assistance",
        {
            "median_annual": 75400,
            "income_band": "mid",
            "salary_quintiles": [44000, 57000, 75400, 97000, 145000],
        },
    )


def calculate_company_taxes(
    company: dict,
    tax_rates: dict,
    reference_data: dict,
    country: str = "australia",
) -> dict:
    """
    Calculate all tax components for a single company.

    Args:
        company: Dict with company data (from enriched CSV)
        tax_rates: Full tax rates config
        reference_data: Industry salary and GST consumption reference data
        country: Country key in tax_rates (default: 'australia')

    Returns:
        Full tax breakdown dict matching the output JSON schema
    """
    rates = tax_rates[country]
    income_brackets = rates["income_tax_brackets"]
    medicare_rate = rates["medicare_levy_rate"]
    medicare_low_threshold = rates.get("medicare_levy_low_income_threshold", 26000)
    payroll_tax_config = rates["payroll_tax_by_state"]
    gst_rate = rates["gst_rate"]
    super_rate = rates.get("superannuation_rate", 0.115)
    land_tax_config = rates.get("land_tax", {})

    # --- Basic company info ---
    company_name = company.get("company_name", "Unknown")
    industry = company.get("industry", "Other Services")
    primary_state = company.get("primary_state", "NSW")
    employees_au = int(company.get("employees_au", 0) or 0)
    employees_global = int(company.get("employees_global", 0) or 0)
    state_dist_str = company.get("state_distribution", f"{primary_state}:100")
    avg_salary_override_raw = company.get("avg_salary_override", "")

    avg_salary_override = None
    if avg_salary_override_raw and str(avg_salary_override_raw).strip() not in ("", "nan"):
        try:
            avg_salary_override = float(avg_salary_override_raw)
        except (ValueError, TypeError):
            avg_salary_override = None

    # --- ATO / corporate income data ---
    total_income = float(company.get("total_income_aud", 0) or 0)
    taxable_income = float(company.get("taxable_income_aud", 0) or 0)
    corporate_tax = float(company.get("tax_payable_aud", 0) or 0)
    ato_data_source = company.get("ato_data_source", "estimated")
    is_ato_actual = "ato" in ato_data_source.lower()

    # --- Industry salary data ---
    industry_data = get_industry_data(industry, reference_data)
    income_band = industry_data.get("income_band", "mid")

    # --- Income tax: 5-quintile distribution ---
    if employees_au > 0:
        income_tax_result = calculate_income_tax_quintile_distribution(
            industry_data,
            income_brackets,
            medicare_rate,
            employees_au,
            avg_salary_override,
        )
    else:
        income_tax_result = {
            "avg_income_tax_per_employee": 0,
            "avg_medicare_per_employee": 0,
            "avg_salary_used": 0,
            "median_salary": 0,
            "total_income_tax": 0,
            "total_medicare": 0,
            "quintile_details": [],
            "methodology": "No employees",
        }

    avg_salary = income_tax_result.get("avg_salary_used", industry_data.get("median_annual", 75000))
    avg_after_tax = avg_salary - income_tax_result.get("avg_income_tax_per_employee", 0) - income_tax_result.get("avg_medicare_per_employee", 0)

    # --- Payroll tax ---
    state_distribution = parse_state_distribution(state_dist_str)
    if employees_au > 0:
        payroll_result = calculate_payroll_tax(
            employees_au,
            avg_salary,
            state_distribution,
            payroll_tax_config,
        )
    else:
        payroll_result = {"total_payroll_tax": 0, "breakdown_by_state": {}, "methodology": "No employees"}

    # --- GST estimate ---
    if employees_au > 0:
        gst_result = calculate_gst_estimate(
            employees_au,
            income_band,
            avg_after_tax,
            reference_data["gst_consumption"],
            gst_rate,
        )
    else:
        gst_result = {"gst_per_employee": 0, "total_gst_estimate": 0}

    # --- Land tax estimate (rough, disabled by default in UI) ---
    if employees_au > 0:
        land_tax_result = calculate_land_tax_estimate(
            employees_au,
            income_band,
            land_tax_config,
        )
    else:
        land_tax_result = {"land_tax_per_employee_est": 0, "total_land_tax_estimate": 0}

    # --- Employer super (not a tax, context only) ---
    if employees_au > 0:
        super_result = calculate_employer_super(employees_au, avg_salary, super_rate)
    else:
        super_result = {"super_per_employee": 0, "total_super_cost": 0}

    # --- Resource payments to Crown (royalties + PRRT) ---
    # These are payments to government as resource owner — NOT classified as taxes.
    # Royalties: state-based charges on extracted commodities (iron ore, coal, gas, gold).
    # PRRT: Petroleum Resource Rent Tax on petroleum project profits.
    # Source: company annual reports. Only applicable to mining/petroleum companies.
    def _safe_num(val: object) -> float:
        """Convert a value that may be NaN, None, or a string to a float."""
        try:
            v = float(val)
            return 0.0 if (v != v) else v  # v != v is True only for IEEE NaN
        except (TypeError, ValueError):
            return 0.0

    royalties = _safe_num(company.get("royalties_aud"))
    prrt = _safe_num(company.get("prrt_aud"))
    resource_payments_total = royalties + prrt

    # --- Aggregate totals ---
    taxes_borne = {
        "corporate_income_tax": round(corporate_tax),
        "employer_payroll_tax": payroll_result["total_payroll_tax"],
        "land_tax_estimate": land_tax_result.get("total_land_tax_estimate", 0),
    }
    taxes_collected = {
        "employee_income_tax_withheld": income_tax_result["total_income_tax"],
        "employee_medicare_levy": income_tax_result["total_medicare"],
        "employee_gst_spending_estimate": gst_result["total_gst_estimate"],
    }
    employer_super_cost = super_result["total_super_cost"]

    # Core total = taxes borne (excl. land) + taxes collected (excl. GST)
    total_core = (
        taxes_borne["corporate_income_tax"]
        + taxes_borne["employer_payroll_tax"]
        + taxes_collected["employee_income_tax_withheld"]
        + taxes_collected["employee_medicare_levy"]
        + taxes_collected["employee_gst_spending_estimate"]
    )
    total_full = total_core + taxes_borne["land_tax_estimate"]

    # Employment tax multiplier = total core / corporate tax alone
    multiplier = (
        round(total_core / taxes_borne["corporate_income_tax"], 3)
        if taxes_borne["corporate_income_tax"] > 0
        else None
    )

    # Revenue per employee
    rev_per_employee = (
        round(total_income / employees_au) if employees_au > 0 else None
    )
    tax_per_employee = (
        round(total_core / employees_au) if employees_au > 0 else None
    )

    # OECD-style tax wedge on labour
    # = (employee income tax + medicare + employer payroll tax) / gross labour cost
    gross_labour_cost = employees_au * avg_salary * (1 + super_rate)
    labour_taxes = (
        taxes_collected["employee_income_tax_withheld"]
        + taxes_collected["employee_medicare_levy"]
        + taxes_borne["employer_payroll_tax"]
    )
    oecd_tax_wedge = (
        round(labour_taxes / gross_labour_cost, 4) if gross_labour_cost > 0 else None
    )

    return {
        "id": company_name.lower().replace(" ", "-").replace("/", "-").replace("(", "").replace(")", "")[:40],
        "company": company_name,
        "industry": industry,
        "primary_state": primary_state,
        "resource_payments_to_crown": {
            "royalties": round(royalties),
            "prrt": round(prrt),
            "total": round(resource_payments_total),
            "is_applicable": resource_payments_total > 0,
            "note": (
                "Payments to government as resource owner — NOT classified as taxes. "
                "Royalties: state-based resource charges on extracted commodities. "
                "PRRT: Petroleum Resource Rent Tax on petroleum project profits. "
                "Source: company annual reports FY2023-24."
            ),
        },
        "ato_data": {
            "total_income": round(total_income),
            "taxable_income": round(taxable_income),
            "tax_payable": round(corporate_tax),
            "data_source": ato_data_source,
            "is_ato_actual": is_ato_actual,
            "data_year": "2023-24",
        },
        "employment": {
            "employees_au": employees_au,
            "employees_global": employees_global,
            "avg_salary_aud": avg_salary,
            "median_salary_aud": income_tax_result.get("median_salary", avg_salary),
            "income_band": income_band,
            "salary_source": "avg_salary_override" if avg_salary_override else "ABS industry quintile distribution",
        },
        "taxes_borne": taxes_borne,
        "taxes_collected": taxes_collected,
        "employer_super_cost_not_tax": employer_super_cost,
        "totals": {
            "corporate_only": taxes_borne["corporate_income_tax"],
            "taxes_borne_excl_land": taxes_borne["corporate_income_tax"] + taxes_borne["employer_payroll_tax"],
            "taxes_collected_core": taxes_collected["employee_income_tax_withheld"] + taxes_collected["employee_medicare_levy"],
            "total_ttc_core": total_core,
            "total_ttc_full_incl_land": total_full,
        },
        "metrics": {
            "employment_tax_multiplier": multiplier,
            "tax_per_employee_aud": tax_per_employee,
            "revenue_per_employee_aud": rev_per_employee,
            "oecd_tax_wedge_on_labour": oecd_tax_wedge,
            "corporate_tax_as_pct_of_total": (
                round(taxes_borne["corporate_income_tax"] / total_core, 4)
                if total_core > 0
                else None
            ),
            "effective_total_rate_on_income": (
                round(total_core / total_income, 4) if total_income > 0 else None
            ),
        },
        "methodology_notes": {
            "income_tax": income_tax_result.get("methodology"),
            "gst": gst_result.get("methodology"),
            "payroll_tax": payroll_result.get("methodology"),
            "land_tax": land_tax_result.get("warning"),
        },
    }
