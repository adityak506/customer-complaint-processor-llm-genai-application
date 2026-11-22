import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Base & Directory Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

STRUCTURED_DIR = OUTPUT_DIR / "structured_data"
EMAILS_DIR = OUTPUT_DIR / "customer_emails"
SUMMARIES_DIR = OUTPUT_DIR / "case_summaries"
FINAL_REPORT_PATH = OUTPUT_DIR / "final_report.csv"

# Supported Input File Types
SUPPORTED_FORMATS = {".txt", ".pdf", ".docx"}

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
TEMPERATURE_EXTRACTION = 0.0
TEMPERATURE_GENERATION = 0.2

# Centralized Logging Setup
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

_file_handler = logging.FileHandler(LOGS_DIR / "project.log", encoding="utf-8")
_file_handler.setFormatter(_formatter)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_formatter)

logging.basicConfig(level=logging.INFO, handlers=[_file_handler, _console_handler])
logger = logging.getLogger("ComplaintProcessor")