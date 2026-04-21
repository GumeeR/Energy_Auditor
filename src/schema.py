from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator
from src.security import (
    MAX_BUSINESS_PROMPT_LEN, MAX_DATASET_REF_LEN, MAX_FACILITY_LEN,
    MAX_PERIOD_LEN, sanitize_prompt, validar_ref_simple,
)

class StatusEnum(str, Enum):
    success = "success"
    warning = "warning"
    error = "error"

class ConfidenceEnum(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"

class JobRequest(BaseModel):
    dataset_ref: str = Field(..., max_length=MAX_DATASET_REF_LEN,
                             description="Nombre del CSV dentro de data/dataset/")
    period: Optional[str] = Field(None, max_length=MAX_PERIOD_LEN)
    facility_filter: Optional[str] = Field(None, max_length=MAX_FACILITY_LEN)
    business_prompt: Optional[str] = Field(
        "Generate structured findings and preliminary recommendations",
        max_length=MAX_BUSINESS_PROMPT_LEN,
    )

    @field_validator("period")
    @classmethod
    def _v_period(cls, v):
        return validar_ref_simple(v, MAX_PERIOD_LEN, "period")

    @field_validator("facility_filter")
    @classmethod
    def _v_facility(cls, v):
        return validar_ref_simple(v, MAX_FACILITY_LEN, "facility_filter")

    @field_validator("business_prompt")
    @classmethod
    def _v_prompt(cls, v):
        return sanitize_prompt(v, MAX_BUSINESS_PROMPT_LEN)

class Summary(BaseModel):
    period: str
    dataset_ref: str

class Metric(BaseModel):
    name: str
    value: Union[float, int, str]
    unit: str
    source: str = "deterministic"

class Evidence(BaseModel):
    dataset_fields: List[str]
    document_refs: List[str]

class Finding(BaseModel):
    id: str
    type: str
    statement: str
    evidence: Evidence
    confidence: ConfidenceEnum

class Recommendation(BaseModel):
    id: str
    text: str
    based_on_findings: List[str]
    disclaimer: str = "Draft subject to human review"

class WarningItem(BaseModel):
    code: str
    message: str

class Trace(BaseModel):
    prompt_version: str
    documents_used: List[str]
    rules_applied: List[str]

class JobResult(BaseModel):
    job_id: str
    status: StatusEnum
    summary: Summary
    metrics: List[Metric]
    findings: List[Finding]
    recommendations_draft: List[Recommendation]
    warnings: List[WarningItem]
    trace: Trace