from pathlib import Path
from typing import Dict, List, Optional, Tuple
import csv
import datetime as dt
import os
import re
import requests

from sec_api import ExtractorApi, QueryApi
import dotenv


# Create data directory if it doesn't exist.
data_dir = Path("data/")
if not data_dir.exists():
    data_dir.mkdir(parents=True, exist_ok=True)

# Create data/results directory if it doesn't exist.
data_results_dir = Path("data/results")
if not data_results_dir.exists():
    data_results_dir.mkdir(parents=True, exist_ok=True)

# Initialize SEC API.
dotenv.load_dotenv()
SEC_API_KEY = os.getenv("SEC_API_KEY")
if not SEC_API_KEY:
    raise RuntimeError("Missing SEC_API_KEY!")
extractor_api = ExtractorApi(api_key=SEC_API_KEY)
queryApi = QueryApi(api_key=SEC_API_KEY)


def clean_text(text):
    """Clean text by removing whitespace, newlines, and tags for HTMLs/Markdown/tables.

    Also replaces special characters.

    Args:
        text (str): The raw text to clean.

    Returns:
        str: The cleaned text.
    """
    # Remove table tags
    table_pattern = r"<table\b[^>]*>.*?<\/table>"
    text = re.sub(table_pattern, "", text, flags=re.DOTALL | re.IGNORECASE)

    # Replace <br> tags with \n
    br_tag_pattern = r"<br\s*/?>"
    text = re.sub(br_tag_pattern, "\n", text, flags=re.IGNORECASE)

    # Replace special characters
    text = re.sub(r"&#160;+", " ", text)

    # Normalize whitespace
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[^\S\n]+", " ", text)

    # Remove HTML tags
    html_link_pattern = r"<a\b[^>]*>(.*?)<\/a>"
    html_tag_pattern = r"<[^>]*>"
    text = re.sub(html_link_pattern, r"\1", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(html_tag_pattern, "", text, flags=re.DOTALL)

    # Remove Markdown tags
    text = re.sub(r"\[.+?\]", "", text)

    return text


def get_10k_sections(
    filing_url_10k: str,
    risk_factors: bool = True,
    biz: bool = True,
    mda: bool = True,
    legal: bool = True,
    accounting: bool = True,
) -> Dict[str, str]:
    """Get the key sections of a 10-K filing and return them as a dictionary.

    Args:
        filing_url_10k: 10-K filing URL from which to extract the relevant section.
        risk_factors: The Risk Factors section. Defaults to True.
        mda: The Management Discussion and Analysis section. Defaults to True.
        biz: The Business section. Defaults to True.
        legal: The Legal Proceedings section. Defaults to True.
        accounting: The Changes in and Disagreements with Accountants on Accounting
            and Financial Disclosure section. Defaults to True.

    Returns:
        A dictionary of the requested sections with cleaned text for each one
        (tables have been removed).
    """

    ## All 10-K sections can be extracted:

    # * 1 - Business
    #     - 1A - Risk Factors
    #     - 1B - Unresolved Staff Comments
    # * 2 - Properties
    # * 3 - Legal Proceedings
    # * 4 - Mine Safety Disclosures
    # * 5 - Market for Registrant’s Common Equity, Related Stockholder Matters and Issuer Purchases of Equity Securities
    # * 6 - Selected Financial Data (prior to February 2021)
    # * 7 - Management’s Discussion and Analysis of Financial Condition and Results of Operations
    #     - 7A - Quantitative and Qualitative Disclosures about Market Risk
    # * 8 - Financial Statements and Supplementary Data
    # * 9 - Changes in and Disagreements with Accountants on Accounting and Financial Disclosure
    #     - 9A - Controls and Procedures
    #     - 9B - Other Information
    # * 10 - Directors, Executive Officers and Corporate Governance
    # * 11 - Executive Compensation
    # * 12 - Security Ownership of Certain Beneficial Owners and Management and Related Stockholder Matters
    # * 13 - Certain Relationships and Related Transactions, and Director Independence
    # * 14 - Principal Accountant Fees and Services

    data = {}

    # get the standardized and cleaned text of section 1A "Risk Factors"
    if risk_factors:
        data["risk_factors"] = clean_text(
            extractor_api.get_section(filing_url_10k, "1A", "text")
        )
    if biz:
        data["biz"] = clean_text(extractor_api.get_section(filing_url_10k, "1", "text"))
    if mda:
        data["mda"] = clean_text(extractor_api.get_section(filing_url_10k, "7", "text"))
    if legal:
        data["legal"] = clean_text(
            extractor_api.get_section(filing_url_10k, "3", "text")
        )
    if accounting:
        data["accounting"] = clean_text(
            extractor_api.get_section(filing_url_10k, "9", "text")
        )

    return data


def get_10k_filing_urls(
    cik: str, start_date: Optional[str] = None, end_date: Optional[str] = None
) -> Dict[str, str]:
    """Get a list of 10-K filing URLs for a given CIK and date range.

    Args:
        cik: The Central Index Key (CIK) of the company.
        start_date: The start date of the date range. Defaults to None, which
            will use 5 years prior to the end_date.
        end_date: The end date of the date range. Defaults to None, which
            will then use today's date.

    Returns:
        A diction of 10-K filing URLs with the period of report date as the key.
    """
    cik = str(int(cik))  # Remove leading zeros.
    if not end_date:
        end_date = dt.date.today().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (
            dt.datetime.strptime(end_date, "%Y-%m-%d") - dt.timedelta(weeks=52 * 5)
        ).strftime("%Y-%m-%d")

    query = {
        "query": {
            "query_string": {
                "query": (
                    f"cik:({cik}) "
                    f"AND filedAt:[{start_date}T00:00:00.000 TO {end_date}T00:00:00.000] "
                    'AND formType:"10-K"'
                ),
                "time_zone": "America/New_York",
            }
        },
        "from": "0",
        "size": "10",
        "sort": [{"filedAt": {"order": "desc"}}],
    }
    filings = queryApi.get_filings(query)
    if not filings:
        return {}
    links = [
        {filing.get("periodOfReport"): filing["linkToFilingDetails"]}
        for filing in filings["filings"]
        if filing["formType"] == "10-K"
    ]
    annual_10k_filings = {date: link for item in links for date, link in item.items()}

    return annual_10k_filings


def get_sec_data(filings: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
    """Get the key sections of a 10-K filing and return them as a dictionary.

    Also include the prior two years of 10-K MDA sections.

    Args:
        filings: A dictionary of 10-K filings with the date as the key and the
            URL to the SEC 10-K as the value.

    Returns:
        A tuple pair consisting of:
        a) The date of the most recent 10-K filing (accounting year end), and
        b) A dictionary of the requested sections with cleaned text for each one
           (tables have been removed).
           The most recent MDA section is included as 'mda'. The prior year's MDA
           is included as 'prior_mda'. The MDA from two years ago is included as
           'prior_prior_mda'.
    """
    if not filings:
        return "", {}
    sorted_dates_desc = sorted(filings, reverse=True)
    most_recent_filing_date = sorted_dates_desc[0]
    url = filings[most_recent_filing_date]
    data = get_10k_sections(url)
    if not data:
        return "", {}
    if len(sorted_dates_desc) > 1:
        prior_date = sorted_dates_desc[1]
        url = filings[prior_date]
        data["prior_mda"] = get_10k_sections(
            url, mda=True, biz=False, risk_factors=False, legal=False, accounting=False
        )["mda"]
    if len(sorted_dates_desc) > 2:
        prior_date = sorted_dates_desc[2]
        url = filings[prior_date]
        data["prior_prior_mda"] = get_10k_sections(
            url, mda=True, biz=False, risk_factors=False, legal=False, accounting=False
        )["mda"]

    return most_recent_filing_date, data


def download_csv_from_url() -> None:
    """Download the CIK to Ticker mapping CSV from GitHub."""
    url = (
        "https://raw.githubusercontent.com/jadchaar/sec-cik-mapper/"
        "main/mappings/stocks/mappings.csv"
    )
    response = requests.get(url)
    if response.status_code == 200:
        with open("data/cik_mappings.csv", "wb") as file:
            file.write(response.content)


def read_cik_mapping_from_csv() -> Dict[str, Dict[str, str]]:
    """Read the CIK to Ticker mapping CSV into a dictionary."""
    file_path = "data/cik_mappings.csv"
    if not os.path.exists(file_path):
        download_csv_from_url()
    cik_mapping = {}
    with open(file_path, "r", newline="") as csvfile:
        csv_reader = csv.DictReader(csvfile)
        for row in csv_reader:
            cik_mapping[row["CIK"]] = {
                "Ticker": row["Ticker"],
                "Name": row["Name"],
                "Exchange": row["Exchange"],
            }
    return cik_mapping


def get_ciks(filename: str) -> List[str]:
    """Get a list of CIKs from a file."""
    ciks = []
    with open(filename, "r") as fin:
        for cik in fin:
            ciks.append(cik.strip())
    return ciks
