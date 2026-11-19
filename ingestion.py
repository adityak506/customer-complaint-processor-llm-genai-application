# Multi-format file reader (.txt, .pdf, .docx)

from pathlib import Path
from pypdf import PdfReader
import docx

from config import SUPPORTED_FORMATS

def extract_text(file_path: Path) -> str:
    """Extracts text from .txt, .pdf, or .docx documents."""
    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported file format: {ext}")

    if ext == ".txt":
        text = file_path.read_text(encoding="utf-8").strip()
    elif ext == ".pdf":
        reader = PdfReader(str(file_path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    elif ext == ".docx":
        doc = docx.Document(str(file_path))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()

    if not text:
        raise ValueError(f"No extractable text found in {file_path.name}")

    return text