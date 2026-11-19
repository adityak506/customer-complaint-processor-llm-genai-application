# 🤖 Customer Complaint Processor — LLM Application

An end-to-end **LangChain + OpenAI** batch pipeline that automatically ingests customer complaint documents, extracts structured data, generates professional response emails, and produces internal management case summaries — all in a single run.

---

## ✨ Features

- 📄 **Multi-format ingestion** — reads `.txt`, `.pdf`, and `.docx` complaint files
- 🧠 **Structured extraction** — uses OpenAI with Pydantic schema enforcement to pull key fields (customer info, category, status, escalation flag, etc.)
- 📧 **Auto-generated response emails** — polite, factual customer emails drafted by the LLM
- 📋 **Management case summaries** — concise Markdown reports for internal teams
- ⚡ **Parallel LLM calls** — email and summary generation run concurrently via `RunnableParallel`
- 📊 **Consolidated CSV report** — all cases aggregated into a single `final_report.csv`
- 🔍 **Observability logging** — structured timestamped logs for every processing step

---

## 🏗️ Architecture

```
data/
  complaint_001.txt
  complaint_002.pdf       ──► ingestion.py (extract_text)
  complaint_003.docx               │
                                   ▼
                          workflow.py (LangChain Runnables)
                          ┌────────────────────────────────┐
                          │  Step 1: Structured Extraction  │
                          │  (extraction_chain → Pydantic)  │
                          └───────────────┬────────────────┘
                                          │
                          ┌──────────────▼──────────────────┐
                          │     RunnableParallel             │
                          │  ┌──────────┐  ┌─────────────┐  │
                          │  │  Email   │  │   Summary   │  │
                          │  │  Chain   │  │    Chain    │  │
                          │  └──────────┘  └─────────────┘  │
                          └─────────────────────────────────┘
                                          │
                          ┌──────────────▼──────────────────┐
                          │           output/                │
                          │  structured_data/*.json          │
                          │  customer_emails/*_email.txt     │
                          │  case_summaries/*_summary.md     │
                          │  final_report.csv                │
                          └─────────────────────────────────┘
```

---

## 📁 Project Structure

```
customer-complaint-processor-llm-application/
│
├── data/                        # Input complaint documents (txt, pdf, docx)
│
├── output/                      # Generated outputs (git-ignored)
│   ├── structured_data/         # Per-complaint JSON files
│   ├── customer_emails/         # Per-complaint response emails
│   ├── case_summaries/          # Per-complaint Markdown summaries
│   └── final_report.csv         # Consolidated report across all complaints
│
├── config.py                    # Paths, LLM settings, logging setup
├── ingestion.py                 # Multi-format text extractor
├── schemas.py                   # Pydantic schema for structured output
├── workflow.py                  # LangChain Runnable pipeline
├── main.py                      # Batch runner entry point
│
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
└── .gitignore
```

---

## 🧩 Extracted Schema Fields

Each complaint document is mapped to the following structured fields via `ComplaintSchema`:

| Field | Description |
|---|---|
| `customer_name` | Full name or `'Unknown'` |
| `email` | Customer email (if present) |
| `phone_number` | Customer phone (if present) |
| `complaint_category` | Billing / Technical / Delivery / Service |
| `issue_description` | Concise summary of the issue |
| `resolution_provided` | Resolution given, or `'None yet'` |
| `complaint` | `Yes` / `No` — is it an actual complaint? |
| `escalation_required` | `Yes` / `No` |
| `supporting_document_available` | `Yes` / `No` |
| `overall_case_status` | `Open` / `In Progress` / `Resolved` / `Escalated` |

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/adityak506/customer-complaint-processor-llm-genai-application.git
cd customer-complaint-processor-llm-genai-application
```

### 2. Create & Activate a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

```bash
cp .env.example .env
```

Open `.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=sk-...your-key-here...
```

> **Optional:** Set a custom model (defaults to `gpt-4o-mini`):
> ```env
> MODEL_NAME=gpt-4o
> ```

### 5. Add Complaint Documents

Place your complaint files in the `data/` folder. Supported formats:

- `.txt` — plain text
- `.pdf` — PDF documents
- `.docx` — Word documents

### 6. Run the Pipeline

```bash
python main.py
```

---

## 📤 Output

After running, the `output/` directory will contain:

```
output/
├── structured_data/
│   ├── complaint_001.json
│   └── ...
├── customer_emails/
│   ├── complaint_001_email.txt
│   └── ...
├── case_summaries/
│   ├── complaint_001_summary.md
│   └── ...
└── final_report.csv
```

### Sample `final_report.csv` columns

```
file_name, customer_name, email, phone_number, complaint_category,
issue_description, resolution_provided, complaint, escalation_required,
supporting_document_available, overall_case_status
```

---

## 🛠️ Tech Stack

| Library | Purpose |
|---|---|
| [LangChain](https://python.langchain.com/) | LLM orchestration & Runnables pipeline |
| [OpenAI GPT-4o-mini](https://platform.openai.com/) | LLM for extraction & generation |
| [Pydantic v2](https://docs.pydantic.dev/) | Structured output schema enforcement |
| [pypdf](https://github.com/py-pdf/pypdf) | PDF text extraction |
| [python-docx](https://python-docx.readthedocs.io/) | Word document text extraction |
| [pandas](https://pandas.pydata.org/) | CSV report generation |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | Environment variable management |

---

## ⚙️ Configuration

All configuration lives in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `MODEL_NAME` | `gpt-4o-mini` | OpenAI model (overridable via `.env`) |
| `TEMPERATURE_EXTRACTION` | `0.0` | Deterministic structured extraction |
| `TEMPERATURE_GENERATION` | `0.2` | Slightly creative email/summary generation |
| `SUPPORTED_FORMATS` | `.txt`, `.pdf`, `.docx` | Accepted input file types |

---

## 📝 License

This project is for educational and research purposes.
