from typing import Literal
from pydantic import BaseModel, Field, field_validator

Severity = Literal["Critical", "Warning", "Normal"]


class LabInput(BaseModel):
    test_name: str = Field(min_length=1)
    value: float
    unit: str = Field(min_length=1)
    date: str | None = None

    @field_validator("test_name", "unit")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be empty")
        return value


class LabAnalysis(BaseModel):
    test_name: str
    value: float
    unit: str
    reference_range: str | None = None
    min_reference: float | None = None
    max_reference: float | None = None
    severity: Severity
    route_order: int
    reason: str
    explanation: str
    recommended_followup: str
    disclaimer: str


class AnalyzeRequest(BaseModel):
    labs: list[LabInput] = Field(min_length=1, max_length=500)


class AnalyzeResponse(BaseModel):
    results: list[LabAnalysis]
    summary: dict[str, int]
