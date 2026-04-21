from pydantic import BaseModel, Field
from typing import List, Optional, Union
from enum import Enum

# Valores fijos
class StatusEnum(str, Enum):
    success = "success"
    warning = "warning"
    error = "error"

class ConfidenceEnum(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"

# Entrada
class JobRequest(BaseModel):
    dataset_ref: str = Field(..., description="nombre del csv dentro de data/datasets/")
    period: Optional[str] = None
    facility_filter: Optional[str] = None
    business_prompt: Optional[str] = "Generate structured findings and preliminary recommendations"

# Salida
class Summary(BaseModel):
    period: str
    dataset_ref: str

class Metric(BaseModel):
    name: str
    value: Union[float, str]
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

class Warning_(BaseModel):
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
    warnings: List[Warning_]
    trace: Trace