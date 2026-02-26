"""
build_dataset.py
----------------
Build the final processed JSON dataset for the web application.

This script:
1. Loads the enriched companies CSV (manually curated with employee data)
2. Optionally merges in the ATO transparency data (if downloaded)
3. Calculates all tax components using calculate_taxes.py
4. Outputs data/processed/australia_{year}.json

Usage:
    python pipeline/build_dataset.py
    python pipeline/build_dataset.py --year 2023-24
    python pipeline/build_dataset.py --no-ato-merge
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import datetime

import pandas as pd

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.calculate_taxes import (
    calculate_company_taxes,
    load_config,
    load_reference_data,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_enriched_companies(enriched_path: str) -> pd.DataFrame:
    """Load the manually curated enriched companies CSV."""
    df = pd.read_csv(enriched_path, low_memory=False)
    print(f"Loaded {len(df)} companies from enriched CSV")
    # Drop any rows where company_name is clearly a comment/header
    df = df[~df["company_name"].astype(str).str.startswith("#")]
    df = df[~df["company_name"].astype(str).str.startswith("Ramsay")]  # dedup
    df = df.dropna(subset=["company_name"])
    df["company_name"] = df["company_name"].astype(str).str.strip()
    # Remove clearly invalid rows
    df = df[df["company_name"].str.len() > 2]
    return df.reset_index(drop=True)


def merge_ato_data(enriched_df: pd.DataFrame, ato_df: pd.DataFrame) -> pd.DataFrame:
    """
    Attempt to merge ATO transparency data into the enriched DataFrame.

    Matching is done by fuzzy company name matching. When ATO data is found,
    it overrides the estimated values from the enriched CSV.
    """
    if ato_df.empty:
        print("No ATO data to merge — using enriched CSV financial estimates only")
        return enriched_df

    print(f"Merging ATO data ({len(ato_df)} entities) with enriched companies...")

    ato_df = ato_df.copy()
    ato_df["entity_name_lower"] = ato_df["entity_name"].astype(str).str.lower().str.strip()

    matched_count = 0
    for idx, row in enriched_df.iterrows():
        company = str(row.get("company_name", "")).lower().strip()
        # Try exact match first
        match = ato_df[ato_df["entity_name_lower"] == company]
        if match.empty:
            # Try partial: each word of company name appears in ATO name
            words = [w for w in company.split() if len(w) > 3]
            for _, ato_row in ato_df.iterrows():
                ato_name = str(ato_row.get("entity_name_lower", ""))
                if all(w in ato_name for w in words[:2]):  # at least first 2 significant words
                    match = ato_df[ato_df["entity_name_lower"] == ato_name]
                    break

        if not match.empty:
            ato_row = match.iloc[0]
            # Update financial fields from ATO data
            if pd.notna(ato_row.get("total_income")):
                enriched_df.at[idx, "total_income_aud"] = ato_row["total_income"]
            if pd.notna(ato_row.get("taxable_income")):
                enriched_df.at[idx, "taxable_income_aud"] = ato_row["taxable_income"]
            if pd.notna(ato_row.get("tax_payable")):
                enriched_df.at[idx, "tax_payable_aud"] = ato_row["tax_payable"]
            enriched_df.at[idx, "ato_data_source"] = "ato_transparency_actual"
            matched_count += 1

    print(f"  Matched {matched_count}/{len(enriched_df)} companies to ATO data")
    unmatched = enriched_df[enriched_df["ato_data_source"] != "ato_transparency_actual"]["company_name"].tolist()
    if unmatched:
        print(f"  Unmatched (using estimates): {', '.join(unmatched[:10])}")
    return enriched_df


def build_dataset(
    year: str = "2023-24",
    merge_ato: bool = True,
    output_dir: str = None,
) -> str:
    """
    Main build function.

    Returns:
        Path to the output JSON file.
    """
    if output_dir is None:
        output_dir = os.path.join(BASE_DIR, "data", "processed")
    os.makedirs(output_dir, exist_ok=True)

    enriched_path = os.path.join(BASE_DIR, "data", "enriched", "companies_enriched.csv")
    ato_csv_path = os.path.join(BASE_DIR, "data", "raw", f"ato_transparency_{year}.csv")

    # Load configs
    print("Loading tax rates and reference data...")
    tax_rates = load_config(os.path.join(BASE_DIR, "config"))
    reference_data = load_reference_data(os.path.join(BASE_DIR, "data", "reference"))

    # Load enriched data
    enriched_df = load_enriched_companies(enriched_path)

    # Optionally merge ATO data
    if merge_ato and os.path.exists(ato_csv_path):
        ato_df = pd.read_csv(ato_csv_path, low_memory=False)
        enriched_df = merge_ato_data(enriched_df, ato_df)
    elif merge_ato:
        print(f"ATO data not found at {ato_csv_path}")
        print("  Run: python pipeline/fetch_ato_data.py  to download it")
        print("  Continuing with enriched CSV estimates only...")

    # Calculate taxes for each company
    print(f"\nCalculating tax estimates for {len(enriched_df)} companies...")
    companies = []
    errors = []

    for idx, row in enriched_df.iterrows():
        try:
            company_dict = row.to_dict()
            result = calculate_company_taxes(company_dict, tax_rates, reference_data)
            companies.append(result)
            employees = result["employment"]["employees_au"]
            corp_tax = result["ato_data"]["tax_payable"]
            total_ttc = result["totals"]["total_ttc_core"]
            multiplier = result["metrics"].get("employment_tax_multiplier", "N/A")
            print(
                f"  [{idx+1:3d}] {result['company'][:40]:40s} "
                f"employees={employees:>7,}  "
                f"corp_tax=${corp_tax/1e9:.2f}B  "
                f"TTC=${total_ttc/1e9:.2f}B  "
                f"multiplier={multiplier}"
            )
        except Exception as e:
            errors.append({"company": row.get("company_name", "?"), "error": str(e)})
            print(f"  ERROR processing {row.get('company_name', '?')}: {e}")

    if errors:
        print(f"\nWARNING: {len(errors)} companies had errors: {[e['company'] for e in errors]}")

    # Sort by total TTC descending
    companies.sort(key=lambda c: c["totals"]["total_ttc_core"], reverse=True)

    # Compute aggregate statistics
    total_corp_tax = sum(c["ato_data"]["tax_payable"] for c in companies)
    total_ttc = sum(c["totals"]["total_ttc_core"] for c in companies)
    total_employees = sum(c["employment"]["employees_au"] for c in companies)
    total_resource_payments = sum(c["resource_payments_to_crown"]["total"] for c in companies)

    output = {
        "meta": {
            "country": "australia",
            "year": year,
            "generated": datetime.datetime.utcnow().isoformat() + "Z",
            "company_count": len(companies),
            "methodology_version": "1.0",
            "framework": "PwC Total Tax Contribution (TTC) Framework",
            "income_tax_methodology": "5-quintile salary distribution per industry (ABS EEH 2023-24)",
            "gst_methodology": "ABS HES 2021-22 household expenditure survey by income band",
            "ato_data_note": "corporate_income_tax values marked is_ato_actual=true are from the ATO Corporate Tax Transparency dataset. All other financial figures are estimated from company annual reports and public sources.",
            "disclaimer": "Estimates are illustrative. Payroll tax, income tax, GST and land tax figures are modelled estimates based on published industry data and tax rates. They should not be taken as actual tax liabilities.",
            "sources": [
                "ATO Corporate Tax Transparency Report 2023-24: https://www.ato.gov.au/businesses-and-organisations/corporate-tax-measures-and-assurance/large-business/corporate-tax-transparency",
                "ABS Employee Earnings, Hours and Leave Survey (EEH) 2023-24: https://www.abs.gov.au/statistics/labour/earnings-and-work-hours/employee-earnings-hours-and-leave-australia",
                "ABS Household Expenditure Survey 2021-22: https://www.abs.gov.au/statistics/economy/finance/household-expenditure-survey-australia-summary-results",
                "State Revenue Offices: payrolltax.gov.au",
                "PwC Total Tax Contribution Framework: https://www.pwc.com/gx/en/services/tax/publications/total-tax-contribution-framework.html",
                "OECD Taxing Wages 2025: https://www.oecd.org/tax/taxing-wages-20725124.htm",
            ],
        },
        "aggregates": {
            "total_corporate_income_tax": round(total_corp_tax),
            "total_tax_contribution_core": round(total_ttc),
            "total_employees_au": total_employees,
            "total_resource_payments_to_crown": round(total_resource_payments),
            "avg_employment_multiplier": round(
                sum(
                    c["metrics"]["employment_tax_multiplier"]
                    for c in companies
                    if c["metrics"].get("employment_tax_multiplier")
                )
                / max(1, sum(1 for c in companies if c["metrics"].get("employment_tax_multiplier"))),
                3,
            ),
        },
        "companies": companies,
    }

    out_path = os.path.join(output_dir, f"australia_{year}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Also write a JS file for the web app (works on file:// without a server)
    webapp_dir = os.path.join(BASE_DIR, "webapp")
    os.makedirs(webapp_dir, exist_ok=True)
    js_path = os.path.join(webapp_dir, f"dataset_{year.replace('-', '_')}.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(f"/* Auto-generated by build_dataset.py — do not edit manually. */\n")
        f.write(f"window.__DATASETS__ = window.__DATASETS__ || {{}};\n")
        f.write(f'window.__DATASETS__["australia_{year}"] = ')
        json.dump(output, f, separators=(",", ":"), ensure_ascii=False)
        f.write(";\n")

    print(f"\nOutput written to: {out_path}")
    print(f"Web app data:      {js_path}")
    print(f"  Companies: {len(companies)}")
    print(f"  Total corporate tax:  ${total_corp_tax/1e9:.1f}B")
    print(f"  Total TTC (core):     ${total_ttc/1e9:.1f}B")
    print(f"  Total AU employees:   {total_employees:,}")
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Build the processed tax dataset JSON for the web app."
    )
    parser.add_argument("--year", type=str, default="2023-24")
    parser.add_argument(
        "--no-ato-merge",
        action="store_true",
        help="Skip merging ATO transparency data (use enriched CSV estimates only)",
    )
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    build_dataset(
        year=args.year,
        merge_ato=not args.no_ato_merge,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
