"""
FastAPI entry point for the Customer Complaint Processor LLM Application.

Endpoints:
  POST /process           — Upload a single complaint file, get full results back.
  POST /process/batch     — Upload multiple files, process all, return aggregated results.
  GET  /results/{stem}    — Fetch previously saved JSON result for a complaint file.
  GET  /report            — Download the consolidated final_report.csv.
  GET  /health            — Liveness check: confirms API is up and OPENAI_API_KEY is set.
"""

import os
import time
import shutil
import tempfile
import asyncio
import logging
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse

from config import (
    OPENAI_API_KEY,
    OUTPUT_DIR,
    STRUCTURED_DIR,
    EMAILS_DIR,
    SUMMARIES_DIR,
    SUPPORTED_FORMATS,
    logger,
)
from ingestion import extract_text
from workflow import workflow_chain

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Customer Complaint Processor API",
    description=(
        "LangChain + OpenAI pipeline that ingests complaint documents "
        "(.txt / .pdf / .docx), extracts structured data, generates a "
        "customer response email, and writes an internal case summary."
    ),
    version="1.0.0",
)


def _ensure_output_dirs() -> None:
    """Create output sub-directories if they don't exist yet."""
    for folder in [STRUCTURED_DIR, EMAILS_DIR, SUMMARIES_DIR]:
        folder.mkdir(parents=True, exist_ok=True)


def _save_outputs(stem: str, result: dict) -> None:
    """Persist structured JSON, email text, and Markdown summary to disk."""
    extracted = result["extracted"]
    (STRUCTURED_DIR / f"{stem}.json").write_text(
        extracted.model_dump_json(indent=2), encoding="utf-8"
    )
    (EMAILS_DIR / f"{stem}_email.txt").write_text(
        result["customer_email"], encoding="utf-8"
    )
    (SUMMARIES_DIR / f"{stem}_summary.md").write_text(
        result["case_summary"], encoding="utf-8"
    )


def _process_file(file_path: Path) -> dict[str, Any]:
    """
    Core processing logic shared by single and batch endpoints.
    Returns a dict ready for JSON serialisation.
    """
    start = time.perf_counter()
    raw_text = extract_text(file_path)
    result = workflow_chain.invoke(raw_text)
    duration = round(time.perf_counter() - start, 3)

    extracted = result["extracted"]
    _save_outputs(file_path.stem, result)

    logger.info(
        "Processed %s in %.3fs | status=%s | escalation=%s",
        file_path.name,
        duration,
        extracted.overall_case_status,
        extracted.escalation_required,
    )

    return {
        "file_name": file_path.name,
        "processing_time_sec": duration,
        "extracted": extracted.model_dump(),
        "customer_email": result["customer_email"],
        "case_summary": result["case_summary"],
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", summary="Health check")
def health_check():
    """
    Returns 200 if the API is running and the OpenAI API key is configured.
    Returns 503 if the key is missing.
    """
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not set. Add it to your .env file.",
        )
    return {"status": "ok", "model": os.getenv("MODEL_NAME", "gpt-4o-mini")}


@app.post("/process", summary="Process a single complaint file")
async def process_single(file: UploadFile = File(...)):
    """
    Upload one complaint document (.txt, .pdf, or .docx).

    Returns:
    - Structured extracted fields (customer name, category, status, etc.)
    - Auto-generated customer response email
    - Internal management case summary (Markdown)
    - Processing time in seconds
    """
    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{suffix}'. Allowed: {sorted(SUPPORTED_FORMATS)}",
        )

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured.")

    _ensure_output_dirs()

    # Save upload to a named temp file so extract_text can read it correctly.
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        result = await asyncio.to_thread(_process_file, tmp_path)
        # Rename outputs to use the original filename stem
        stem = Path(file.filename).stem
        for src, dst in [
            (STRUCTURED_DIR / f"{tmp_path.stem}.json",    STRUCTURED_DIR / f"{stem}.json"),
            (EMAILS_DIR    / f"{tmp_path.stem}_email.txt", EMAILS_DIR    / f"{stem}_email.txt"),
            (SUMMARIES_DIR / f"{tmp_path.stem}_summary.md", SUMMARIES_DIR / f"{stem}_summary.md"),
        ]:
            if src.exists():
                src.rename(dst)
        result["file_name"] = file.filename
        return JSONResponse(content=result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to process %s: %s", file.filename, exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/process/batch", summary="Process multiple complaint files")
async def process_batch(files: list[UploadFile] = File(...)):
    """
    Upload multiple complaint documents in one request.

    Each file is processed sequentially through the LLM pipeline.
    A consolidated `final_report.csv` is saved to the output/ directory.

    Returns a list of per-file results plus a batch summary.
    """
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured.")

    _ensure_output_dirs()

    results = []
    report_rows = []
    batch_start = time.perf_counter()

    for upload in files:
        suffix = Path(upload.filename).suffix.lower()
        if suffix not in SUPPORTED_FORMATS:
            results.append({
                "file_name": upload.filename,
                "status": "skipped",
                "detail": f"Unsupported format '{suffix}'",
            })
            continue

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(upload.file, tmp)
            tmp_path = Path(tmp.name)

        try:
            result = await asyncio.to_thread(_process_file, tmp_path)
            stem = Path(upload.filename).stem
            for src, dst in [
                (STRUCTURED_DIR / f"{tmp_path.stem}.json",     STRUCTURED_DIR / f"{stem}.json"),
                (EMAILS_DIR    / f"{tmp_path.stem}_email.txt",  EMAILS_DIR    / f"{stem}_email.txt"),
                (SUMMARIES_DIR / f"{tmp_path.stem}_summary.md", SUMMARIES_DIR / f"{stem}_summary.md"),
            ]:
                if src.exists():
                    src.rename(dst)

            result["file_name"] = upload.filename
            result["status"] = "success"
            results.append(result)
            report_rows.append({"file_name": upload.filename, **result["extracted"]})

        except Exception as exc:
            logger.error("Batch: failed %s — %s", upload.filename, exc)
            results.append({
                "file_name": upload.filename,
                "status": "error",
                "detail": str(exc),
            })
            report_rows.append({
                "file_name": upload.filename,
                "overall_case_status": f"ERROR: {exc}",
            })
        finally:
            tmp_path.unlink(missing_ok=True)

    # Save consolidated CSV
    if report_rows:
        report_path = OUTPUT_DIR / "final_report.csv"
        pd.DataFrame(report_rows).to_csv(report_path, index=False, encoding="utf-8")
        logger.info("Batch report saved to %s", report_path)

    total_duration = round(time.perf_counter() - batch_start, 3)
    succeeded = sum(1 for r in results if r.get("status") == "success")
    failed    = sum(1 for r in results if r.get("status") == "error")
    skipped   = sum(1 for r in results if r.get("status") == "skipped")

    return {
        "summary": {
            "total": len(files),
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
            "total_duration_sec": total_duration,
        },
        "results": results,
    }


@app.get("/results/{stem}", summary="Fetch saved result for a complaint")
def get_result(stem: str):
    """
    Retrieve the saved structured JSON for a previously processed complaint.

    `stem` is the filename without extension, e.g. `complaint_001`.
    """
    json_path = STRUCTURED_DIR / f"{stem}.json"
    if not json_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No result found for '{stem}'. Process the file first.",
        )
    import json
    return JSONResponse(content=json.loads(json_path.read_text(encoding="utf-8")))


@app.get("/report", summary="Download the consolidated CSV report")
def download_report():
    """
    Download `output/final_report.csv` — the consolidated results of all
    processed complaints. Only available after running /process/batch or
    the CLI batch runner (main.py).
    """
    report_path = OUTPUT_DIR / "final_report.csv"
    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No report found. Run /process/batch or python main.py first.",
        )
    return FileResponse(
        path=str(report_path),
        media_type="text/csv",
        filename="final_report.csv",
    )
