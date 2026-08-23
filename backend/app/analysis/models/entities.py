"""Extracted Entity Models for ScamCheck Analysis Layer.

STATUS: FULLY IMPLEMENTED (Analysis Data Contracts)

Purpose:
Defines standard schemas for structured entities extracted from opportunity texts,
images (OCR), or PDFs (e.g. organizations, contacts, payment requests, URLs).
Extraction logic is reserved for subsequent phases; these models establish the contract.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class OrganizationEntity(BaseModel):
    """Extracted organization, company, or institution mention."""
    name: str = Field(..., description="Name of the claimed organization or business entity.")
    domain: Optional[str] = Field(default=None, description="Associated website domain if identified.")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Extraction confidence score.")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JobTitleEntity(BaseModel):
    """Extracted job title, role, or position mention."""
    title: str = Field(..., description="Job or internship position title.")
    department: Optional[str] = Field(default=None, description="Department or field of work.")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class EmailEntity(BaseModel):
    """Extracted email address and provider information."""
    email: str = Field(..., description="Extracted email address.")
    domain: Optional[str] = Field(default=None, description="Email domain component.")
    is_free_provider: Optional[bool] = Field(
        default=None,
        description="Whether domain belongs to a free public provider (e.g. gmail, yahoo, hotmail).",
    )


class PhoneEntity(BaseModel):
    """Extracted phone, mobile, or WhatsApp contact number."""
    number: str = Field(..., description="Raw or formatted phone number.")
    country_code: Optional[str] = Field(default=None, description="Identified country calling code.")
    normalized_number: Optional[str] = Field(default=None, description="E.164 formatted telephone number.")


class UrlEntity(BaseModel):
    """Extracted URL, hyperlink, or application portal link."""
    url: str = Field(..., description="Full URL string.")
    domain: Optional[str] = Field(default=None, description="Extracted root or subdomain.")
    path: Optional[str] = Field(default=None, description="URL path component.")
    is_shortened: Optional[bool] = Field(
        default=None,
        description="Whether URL points to a known link shortener (e.g. bit.ly, tinyurl).",
    )


class MonetaryAmountEntity(BaseModel):
    """Extracted currency, stipend, fee, or compensation figure."""
    raw_amount: str = Field(..., description="Exact textual monetary representation (e.g. '₹5,000', '$20/hr').")
    currency: Optional[str] = Field(default=None, description="Currency ISO code or symbol (e.g. 'INR', 'USD', '₹').")
    numeric_value: Optional[float] = Field(default=None, description="Parsed numeric amount.")
    purpose: Optional[str] = Field(
        default=None,
        description="Identified monetary purpose (e.g. 'registration_fee', 'security_deposit', 'salary', 'stipend').",
    )


class PercentageEntity(BaseModel):
    """Extracted percentage or commission figure."""
    raw_percentage: str = Field(..., description="Textual percentage (e.g. '40%', '100% guaranteed').")
    numeric_value: Optional[float] = Field(default=None, description="Parsed float percentage value.")
    context: Optional[str] = Field(default=None, description="Contextual association (e.g. 'commission', 'selection rate').")


class DateEntity(BaseModel):
    """Extracted date, deadline, or time requirement."""
    raw_date: str = Field(..., description="Textual date mention (e.g. '25/10/2026', 'Immediate').")
    parsed_date: Optional[str] = Field(default=None, description="Standardized ISO-8601 date string.")
    date_type: Optional[str] = Field(
        default=None,
        description="Classification of date (e.g. 'deadline', 'start_date', 'interview_date').",
    )


class LocationEntity(BaseModel):
    """Extracted physical location or remote work indication."""
    raw_location: str = Field(..., description="Location string mention.")
    city: Optional[str] = Field(default=None)
    country: Optional[str] = Field(default=None)
    is_remote: Optional[bool] = Field(default=None, description="Whether location denotes work-from-home/remote.")


class PaymentDetailEntity(BaseModel):
    """Extracted payment instruction, bank detail, or UPI handle."""
    payment_type: str = Field(
        ...,
        description="Type of payment requested (e.g. 'registration_fee', 'training_materials', 'laptop_deposit').",
    )
    amount: Optional[str] = Field(default=None, description="Associated payment amount.")
    recipient: Optional[str] = Field(default=None, description="Claimed payee or company account name.")
    upi_id: Optional[str] = Field(default=None, description="Extracted UPI VPA handle if present.")
    method: Optional[str] = Field(default=None, description="Payment channel (e.g. 'UPI', 'Bank Transfer', 'Crypto').")


class ContactInfoEntity(BaseModel):
    """Aggregated contact channels extracted from the opportunity."""
    primary_channel: Optional[str] = Field(default=None, description="Apparent primary communication avenue.")
    emails: List[str] = Field(default_factory=list)
    phone_numbers: List[str] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)
    social_handles: Dict[str, str] = Field(
        default_factory=dict,
        description="Platform handles (e.g. {'telegram': '@hr_recruiter', 'whatsapp': '+91...'}).",
    )


class ExtractedEntities(BaseModel):
    """Unified container for all structured entities extracted from an opportunity."""
    organizations: List[OrganizationEntity] = Field(default_factory=list)
    job_titles: List[JobTitleEntity] = Field(default_factory=list)
    emails: List[EmailEntity] = Field(default_factory=list)
    phone_numbers: List[PhoneEntity] = Field(default_factory=list)
    urls: List[UrlEntity] = Field(default_factory=list)
    monetary_amounts: List[MonetaryAmountEntity] = Field(default_factory=list)
    percentages: List[PercentageEntity] = Field(default_factory=list)
    dates: List[DateEntity] = Field(default_factory=list)
    locations: List[LocationEntity] = Field(default_factory=list)
    payment_details: List[PaymentDetailEntity] = Field(default_factory=list)
    contact_info: Optional[ContactInfoEntity] = Field(default=None)
    raw_entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Generic or unclassified extracted entity bag.",
    )

    model_config = ConfigDict(populate_by_name=True)
