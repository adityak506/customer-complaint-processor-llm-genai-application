from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnableParallel
from schemas import ComplaintSchema
from config import MODEL_NAME, TEMPERATURE_EXTRACTION, TEMPERATURE_GENERATION

load_dotenv()

extraction_llm = ChatOpenAI(model=MODEL_NAME, temperature=TEMPERATURE_EXTRACTION)
generation_llm = ChatOpenAI(model=MODEL_NAME, temperature=TEMPERATURE_GENERATION)

# --- Task 1: Structured Extraction ---
extraction_prompt = ChatPromptTemplate.from_messages([
    ("system", "Extract customer complaint details strictly from the document text. Do not invent facts."),
    ("human", "{document_text}")
])
structured_llm = extraction_llm.with_structured_output(ComplaintSchema)
extraction_chain = extraction_prompt | structured_llm

# --- Task 2: Customer Response Email ---
email_prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "Write a polite, professional customer response email based ONLY on the extracted details and source text. "
        "Address the customer by name (use 'Valued Customer' if Unknown), summarize the issue, and state the resolution/status. "
        "CRITICAL: Do not invent refunds, timelines, or policies not present in the source."
    )),
    ("human", "Extracted Details:\n{extracted_json}\n\nOriginal Document:\n{document_text}")
])
email_chain = email_prompt | generation_llm | StrOutputParser()

# --- Task 3: Management Case Summary ---
summary_prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "Create a concise internal management case summary in Markdown with these exact sections:\n"
        "- **Case Overview**\n"
        "- **Key Issue**\n"
        "- **Action Taken**\n"
        "- **Current Status**\n"
        "- **Recommended Next Action**\n"
        "Base all details strictly on the provided facts."
    )),
    ("human", "Extracted Details:\n{extracted_json}\n\nOriginal Document:\n{document_text}")
])
summary_chain = summary_prompt | generation_llm | StrOutputParser()


# --- Simple Runnables Workflow (Sequential -> Parallel) ---
def run_extraction_step(document_text: str) -> dict:
    extracted_obj: ComplaintSchema = extraction_chain.invoke({"document_text": document_text})
    return {
        "document_text": document_text,
        "extracted": extracted_obj,
        "extracted_json": extracted_obj.model_dump_json(indent=2),
    }


workflow_chain = (
    RunnableLambda(run_extraction_step)
    | RunnableParallel(
        extracted=RunnableLambda(lambda x: x["extracted"]),
        customer_email=email_chain,
        case_summary=summary_chain,
    )
)