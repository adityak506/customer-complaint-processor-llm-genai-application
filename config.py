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
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("ComplaintProcessor")