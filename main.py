
from config import (
    OPENAI_API_KEY,
    OUTPUT_DIR,
    DATA_DIR,
    STRUCTURED_DIR,
    EMAILS_DIR,
    SUMMARIES_DIR,
    FINAL_REPORT_PATH,
    SUPPORTED_FORMATS,
    logger,
)

import os
import logging
from pathlib import Path
import pandas as pd
from ingestion import extract_text, SUPPORTED_FORMATS
from workflow import workflow_chain


def setup_directories() -> None:
    for folder in [STRUCTURED_DIR, EMAILS_DIR, SUMMARIES_DIR]:
        folder.mkdir(parents=True, exist_ok=True)


def run_batch() -> None:
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

    logging.info(f"Found {len(files)} document(s) to process.")
    report_rows = []

    for file_path in files:
        logging.info(f"Processing: {file_path.name}")
        try:
            # 1. Document Ingestion[cite: 1]
            raw_text = extract_text(file_path)

            # 2. Execute LangChain Runnable Workflow[cite: 1, 3]
            result = workflow_chain.invoke(raw_text)
            extracted = result["extracted"]

            # 3. Save Individual Outputs[cite: 1, 3]
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

            # 4. Append row to consolidated report[cite: 1, 3]
            report_rows.append({"file_name": file_path.name, **extracted.model_dump()})
            logging.info(f"Successfully processed: {file_path.name}")

        except Exception as e:
            logging.error(f"Failed to process {file_path.name}: {e}")
            report_rows.append({
                "file_name": file_path.name,
                "overall_case_status": f"ERROR: {e}",
            })

    # Export consolidated CSV report[cite: 1, 3]
    report_path = OUTPUT_DIR / "final_report.csv"
    pd.DataFrame(report_rows).to_csv(report_path, index=False, encoding="utf-8")
    logging.info(f"Batch complete. Consolidated report saved to {report_path}")


if __name__ == "__main__":
    run_batch()