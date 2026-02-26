"""
fetch_ato_data.py
-----------------
Download the ATO Corporate Tax Transparency dataset from data.gov.au.

The ATO publishes annual data on entities with total income >= $100M.
Dataset URL: https://data.gov.au/data/dataset/corporate-transparency

This script:
1. Queries the data.gov.au CKAN API to find the most recent resource URL
2. Downloads the Excel/CSV file
3. Parses and normalises the columns
4. Saves to data/raw/ato_transparency_{year}.csv

Usage:
    python pipeline/fetch_ato_data.py
    python pipeline/fetch_ato_data.py --year 2022-23
    python pipeline/fetch_ato_data.py --list-years
"""

import argparse
import os
import sys
import time
import json
import re
import requests
import pandas as pd

DATASET_ID = "corporate-transparency"
CKAN_API_BASE = "https://data.gov.au/api/3/action"
RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

# Known column name mappings across different years of ATO releases
# The ATO has occasionally renamed columns between years.
COLUMN_ALIASES = {
    "entity_name": [
        "Entity name or business name",
        "Name",
        "Entity name",
        "entity name",
        "Company name",
    ],
    "total_income": [
        "Total income",
        "Total income ($)",
        "total income",
        "Total Income",
    ],
    "taxable_income": [
        "Taxable income or loss",
        "Taxable income",
        "taxable income or loss",
        "Taxable Income",
    ],
    "tax_payable": [
        "Income tax payable",
        "Tax payable",
        "income tax payable",
        "Income Tax Payable",
        "Tax Payable",
    ],
    "abn": [
        "ABN",
        "abn",
        "Tax file number (TFN) / ABN",
    ],
    "industry": [
        "Industry code",
        "ANZSIC industry code",
        "Industry",
    ],
    "country_of_tax_residence": [
        "Country of tax residence",
        "Tax residence",
    ],
    "international_related_party_dealings": [
        "Relates to international related party dealings",
        "International related party dealings",
    ],
}


def query_ckan_api(dataset_id: str) -> dict:
    """Query the data.gov.au CKAN API to get dataset metadata."""
    url = f"{CKAN_API_BASE}/package_show"
    params = {"id": dataset_id}
    print(f"Querying CKAN API: {url}?id={dataset_id}")
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not data.get("success"):
        raise ValueError(f"CKAN API error: {data.get('error')}")
    return data["result"]


def list_available_years(dataset_metadata: dict) -> list[dict]:
    """Extract available data years from dataset resources."""
    resources = dataset_metadata.get("resources", [])
    years = []
    for r in resources:
        name = r.get("name", "")
        url = r.get("url", "")
        fmt = r.get("format", "").upper()
        # Match year patterns like "2023-24", "2022-23", "2021-22"
        year_match = re.search(r"(\d{4}-\d{2})", name)
        if year_match and fmt in ("CSV", "XLSX", "XLS", "ZIP"):
            years.append({
                "year": year_match.group(1),
                "name": name,
                "url": url,
                "format": fmt,
                "id": r.get("id"),
            })
    # Sort newest first
    years.sort(key=lambda x: x["year"], reverse=True)
    return years


def download_resource(url: str, dest_path: str) -> str:
    """Download a file from URL to dest_path with progress indication."""
    print(f"Downloading: {url}")
    print(f"Destination: {dest_path}")

    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    total = int(response.headers.get("content-length", 0))
    downloaded = 0

    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  {downloaded:,} / {total:,} bytes ({pct:.1f}%)", end="")
    print()
    return dest_path


def normalise_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise DataFrame column names to standard internal names.
    Handles variation in ATO column naming across years.
    """
    col_map = {}
    for standard_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df.columns:
                col_map[alias] = standard_name
                break

    df = df.rename(columns=col_map)

    # Keep only columns we have standard names for
    known_cols = list(COLUMN_ALIASES.keys())
    existing_known = [c for c in known_cols if c in df.columns]
    df = df[existing_known].copy()

    return df


def parse_ato_file(file_path: str) -> pd.DataFrame:
    """
    Parse an ATO transparency file (CSV or Excel) into a normalised DataFrame.
    """
    ext = os.path.splitext(file_path)[1].lower()

    print(f"Parsing file: {file_path}")

    if ext in (".xlsx", ".xls"):
        # ATO Excel files often have metadata rows at the top; try to find the header
        # by looking for the row containing "Entity name" or similar
        xl = pd.ExcelFile(file_path)
        sheet_name = xl.sheet_names[0]
        print(f"  Excel sheet: {sheet_name}")

        # Try reading with different header rows
        for header_row in range(0, 10):
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
            # Check if this looks like the right header
            cols_lower = [str(c).lower() for c in df.columns]
            if any("entity" in c or "income" in c or "taxable" in c for c in cols_lower):
                print(f"  Found data header at row {header_row}")
                break
        else:
            df = pd.read_excel(file_path, sheet_name=sheet_name)

    elif ext == ".csv":
        # Try UTF-8 first, then latin-1
        try:
            df = pd.read_csv(file_path, encoding="utf-8", low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding="latin-1", low_memory=False)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    print(f"  Raw shape: {df.shape}")
    print(f"  Raw columns: {list(df.columns[:10])}")

    df = normalise_column_names(df)

    # Clean numeric columns
    for col in ["total_income", "taxable_income", "tax_payable"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r"[,$\s]", "", regex=True),
                errors="coerce",
            )

    # Drop rows with no entity name
    if "entity_name" in df.columns:
        df = df.dropna(subset=["entity_name"])
        df = df[df["entity_name"].astype(str).str.strip() != ""]

    print(f"  Normalised shape: {df.shape}")
    return df


def fetch_ato_data(year: str = None, output_dir: str = None) -> str:
    """
    Main function: fetch ATO transparency data for a given year.

    Args:
        year: Year string like "2023-24". If None, fetches the most recent year.
        output_dir: Directory to save the CSV. Defaults to data/raw/

    Returns:
        Path to the saved CSV file.
    """
    if output_dir is None:
        output_dir = RAW_DATA_DIR
    os.makedirs(output_dir, exist_ok=True)

    # Get dataset metadata
    try:
        metadata = query_ckan_api(DATASET_ID)
    except Exception as e:
        print(f"ERROR: Could not query CKAN API: {e}")
        print("Please check your internet connection or try downloading manually from:")
        print("  https://data.gov.au/data/dataset/corporate-transparency")
        sys.exit(1)

    available = list_available_years(metadata)
    if not available:
        print("ERROR: No downloadable resources found in dataset.")
        print("Resources found:")
        for r in metadata.get("resources", []):
            print(f"  - {r.get('name')} ({r.get('format')}) {r.get('url', '')[:80]}")
        sys.exit(1)

    print(f"\nAvailable years:")
    for a in available:
        print(f"  {a['year']:10s}  {a['format']:5s}  {a['name']}")

    # Select the year to download
    if year is None:
        selected = available[0]
        print(f"\nNo year specified — using most recent: {selected['year']}")
    else:
        selected = next((a for a in available if a["year"] == year), None)
        if selected is None:
            print(f"ERROR: Year '{year}' not found. Available: {[a['year'] for a in available]}")
            sys.exit(1)

    year_str = selected["year"]
    ext = ".xlsx" if selected["format"] in ("XLSX", "XLS") else ".csv"
    raw_file = os.path.join(output_dir, f"ato_transparency_{year_str}{ext}")
    csv_file = os.path.join(output_dir, f"ato_transparency_{year_str}.csv")

    # Download if not already present
    if os.path.exists(csv_file):
        print(f"\nAlready downloaded: {csv_file}")
    else:
        download_resource(selected["url"], raw_file)
        # Parse and save as CSV
        df = parse_ato_file(raw_file)
        df.to_csv(csv_file, index=False)
        print(f"\nSaved normalised CSV: {csv_file}")
        print(f"  Rows: {len(df):,}")

    return csv_file


def load_ato_data(year: str = "2023-24", data_dir: str = None) -> pd.DataFrame:
    """
    Load already-downloaded ATO data from data/raw/.
    Returns an empty DataFrame if the file doesn't exist.
    """
    if data_dir is None:
        data_dir = RAW_DATA_DIR

    csv_file = os.path.join(data_dir, f"ato_transparency_{year}.csv")
    if os.path.exists(csv_file):
        return pd.read_csv(csv_file, low_memory=False)
    return pd.DataFrame()


def main():
    parser = argparse.ArgumentParser(
        description="Download and parse ATO Corporate Tax Transparency data."
    )
    parser.add_argument(
        "--year",
        type=str,
        default=None,
        help="Year to download, e.g. '2023-24'. Defaults to most recent.",
    )
    parser.add_argument(
        "--list-years",
        action="store_true",
        help="List available years and exit.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for raw data. Defaults to data/raw/",
    )
    args = parser.parse_args()

    if args.list_years:
        metadata = query_ckan_api(DATASET_ID)
        available = list_available_years(metadata)
        print("Available years in ATO Corporate Tax Transparency dataset:")
        for a in available:
            print(f"  {a['year']:10s}  {a['format']:5s}  {a['name']}")
        return

    fetch_ato_data(year=args.year, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
