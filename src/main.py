from argparse import ArgumentParser
from typing import List, Optional
import os

from langchain.chat_models import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from loguru import logger
import dotenv

from src.prompts import template
from src.utils import (
    get_ciks,
    get_10k_filing_urls,
    get_sec_data,
    read_cik_mapping_from_csv,
)


# Constants.
MAX_TOKENS = 10_000  # Max tokens to sample from the model.

# Load environment variables.
dotenv.load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise RuntimeError("Missing ANTHROPIC_API_KEY!")
SEC_API_KEY = os.getenv("SEC_API_KEY")
if not SEC_API_KEY:
    raise RuntimeError("Missing SEC_API_KEY!")


def main(ciks: Optional[List[str]]) -> None:
    """Run the main program.

    Args:
        ciks: A list of Central Index Keys (CIKs) for which to get 10-K data
            and generate a response from the model.

    Returns:
        None.  Results are saved in `data/results`.
    """
    # Get CIK mapping from CSV file.
    cik_mapping = read_cik_mapping_from_csv()

    # Initialize APIs.
    model = ChatAnthropic(
        model="claude-2", temperature=0, max_tokens_to_sample=MAX_TOKENS
    )

    # Get Central Index Keys (CIKs) and SEC data.
    prompt = ChatPromptTemplate.from_template(template)

    if not ciks:
        # Ust return i no CIKs are given and none are found in the file data/ciks.txt.
        logger.info("No CIKs found.")
        return
    for n, cik in enumerate(ciks, start=1):
        if not cik:
            continue  # Skip empty CIKs.
        mappings = cik_mapping.get(cik, {})
        ticker = mappings.get("Ticker") or "No Ticker"
        company_name = mappings.get("Name") or "No Name"
        exchange = mappings.get("Exchange") or "No Exchange"
        header = f"# {company_name} ({exchange}: {ticker})\n\n"
        logger.info(
            f"{n}/{len(ciks)}: Getting 10-K data for CIK {cik} ({company_name})..."
        )
        filings = []
        try:
            filings = get_10k_filing_urls(cik=cik)
        except Exception as e:
            logger.error(f"Error getting 10-K filings for CIK {cik}: {e}")
            continue
        accounting_year_end = ""
        sec_data = {}
        if filings:
            try:
                accounting_year_end, sec_data = get_sec_data(filings=filings)
                header += f"### Accounting Year End: {accounting_year_end}\n\n"
            except Exception as e:
                logger.error(f"Error getting SEC data for CIK {cik}: {e}")
                continue

        # Get the model response given the prompt and SEC data.
        logger.info(f"Getting model response for CIK {cik} ({ticker})...")
        try:
            model_response = model.predict(prompt.format(**sec_data)).strip()
        except Exception as e:
            logger.error(f"Error getting model response for CIK {cik}: {e}, {ticker}")
            continue

        # Save the model response as a markdown file.
        symbol = cik_mapping[cik]
        filename = f"data/results/CIK_{cik}_{ticker}_10K_{accounting_year_end}.md"
        with open(filename, "w") as fout:
            fout.write(header + model_response)


if __name__ == "__main__":
    # Parse command line arguments to get CIKs.
    parser = ArgumentParser()
    # Get CIKs, e.g. '0000320193', '0000789019'
    parser.add_argument("ciks", nargs="*", help="List of Central Index Keys (CIKs)")
    args = parser.parse_args()
    ciks = args.ciks
    if not ciks:
        ciks = get_ciks("data/ciks.txt")

    main(ciks=ciks)
