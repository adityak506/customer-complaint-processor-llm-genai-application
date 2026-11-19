# Pydantic model for structured extraction

from typing import Literal, Optional
from pydantic import BaseModel, Field

class ComplaintSchema(BaseModel):
    customer_name: str = Field(description="Customer's full name, or 'Unknown' if not provided.")
    email: Optional[str] = Field(default=None, description="Customer email address if present.")
    phone_number: Optional[str] = Field(default=None, description="Customer phone number if present.")
    complaint_category: str = Field(description="Category such as Billing, Technical, Delivery, or Service.")
    issue_description: str = Field(description="Concise summary of the customer's issue.")
    resolution_provided: str = Field(description="Resolution already given, or 'None yet' if unresolved.")
    complaint: Literal["Yes", "No"] = Field(description="Whether the document is an actual complaint.")
    escalation_required: Literal["Yes", "No"] = Field(description="Whether escalation is required.")
    supporting_document_available: Literal["Yes", "No"] = Field(description="Whether receipts, logs, or attachments are mentioned.")
    overall_case_status: Literal["Open", "In Progress", "Resolved", "Escalated"] = Field(
        description="Current status of the case."
    )