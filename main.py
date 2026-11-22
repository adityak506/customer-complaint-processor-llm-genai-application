import os
import logging
from pathlib import Path
import pandas as pd

from config import (
    OUTPUT_DIR,
    DATA_DIR,
    STRUCTURED_DIR,
    EMAILS_DIR,
    SUMMARIES_DIR,
    SUPPORTED_FORMATS,
    logger,
)
from ingestion import extract_text
from workflow import workflow_chain


def setup_directories() -> None:
    """Create output sub-directories if they don't exist."""
    for folder in [STRUCTURED_DIR, EMAILS_DIR, SUMMARIES_DIR]:
        folder.mkdir(parents=True, exist_ok=True)


def process_file(file_path: Path) -> dict:
    """
    Process a single complaint document through the LLM workflow.

    Steps:
      1. Extract raw text from the file (txt / pdf / docx).
      2. Run the LangChain workflow  →  structured extraction + email + summary.
      3. Save individual outputs to disk.

    Returns a dict with 'extracted', 'customer_email', and 'case_summary'.
    """
    raw_text = extract_text(file_path)
    result = workflow_chain.invoke(raw_text)
    extracted = result["extracted"]

    stem = file_path.stem
    (STRUCTURED_DIR / f"{stem}.json").write_text(
        extracted.model_dump_json(indent=2), encoding="utf-8"
    )
    (EMAILS_DIR / f"{stem}_email.txt").write_text(
        result["customer_email"], encoding="utf-8"
    )
    (SUMMARIES_DIR / f"{stem}_summary.md").write_text(
        result["case_summary"], encoding="utf-8"
    )

    logger.info("Processed: %s | status=%s", file_path.name, extracted.overall_case_status)
    return result


def run_batch() -> None:
    """Process every supported file in data/ and write a consolidated CSV report."""
    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY not found. Add it to your .env file.")

    setup_directories()

    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True)
        logging.warning("Created empty data/ directory. Add complaint files and re-run.")
        return

    files = sorted(
        f for f in DATA_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS
    )

    if not files:
        logging.warning("No eligible .txt, .pdf, or .docx files found in data/.")
        return

    logging.info("Found %d document(s) to process.", len(files))
    report_rows = []

    for file_path in files:
        try:
            result = process_file(file_path)
            report_rows.append({"file_name": file_path.name, **result["extracted"].model_dump()})
        except Exception as e:
            logging.error("Failed to process %s: %s", file_path.name, e)
            report_rows.append({"file_name": file_path.name, "overall_case_status": f"ERROR: {e}"})

    report_path = OUTPUT_DIR / "final_report.csv"
    pd.DataFrame(report_rows).to_csv(report_path, index=False, encoding="utf-8")
    logging.info("Batch complete. Report saved to %s", report_path)


if __name__ == "__main__":
    run_batch()
