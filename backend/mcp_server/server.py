import json
import os
import re
import pandas as pd
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from google import genai
from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_DIR = Path(__file__).resolve().parents[1]
df = pd.read_csv("data/laboratory_test_results.csv")

mcp = MCPServer(
    "Clinical Lab Analyzer MCP",
    instructions=(
        "Tools for deterministic laboratory reference-range lookup and severity classification, "
        "plus LLM-generated explanations. The orchestrating agent must call these tools in order."
    ),
)


def normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def reference_range_lookup(test_name):
    rows = df[df["Test_Name"] == test_name]

    if rows.empty:
        raise ValueError("Unknown laboratory test")

    row = rows.iloc[0]

    return {
        "test_name": row["Test_Name"],
        "unit": row["Unit"],
        "min_reference": row["Min_Reference"],
        "max_reference": row["Max_Reference"],
        "reference_range": row["Reference_Range"]
    }


@mcp.tool()
def classify_lab(value: float, min_reference: float, max_reference: float) -> dict:
    """Classify a value using a transparent demo severity policy.

    Normal: inside reference interval.
    Warning: outside interval but not beyond the critical multiplier.
    Critical: below 50% of the lower bound or above 150% of the upper bound.
    This is an assignment/demo heuristic, not a clinical decision rule.
    """
    if min_reference > max_reference:
        raise ValueError("min_reference must be <= max_reference")

    if min_reference <= value <= max_reference:
        return {
            "severity": "Normal",
            "reason": "The result is inside the supplied reference interval.",
            "route_order": 3,
        }

    if value < min_reference:
        critical = min_reference > 0 and value < (0.5 * min_reference)
        severity = "Critical" if critical else "Warning"
        reason = (
            f"The result is below the lower reference limit ({min_reference})."
        )
    else:
        critical = value > (1.5 * max_reference)
        severity = "Critical" if critical else "Warning"
        reason = (
            f"The result is above the upper reference limit ({max_reference})."
        )

    return {
        "severity": severity,
        "reason": reason,
        "route_order": 1 if severity == "Critical" else 2,
    }


class Explanation(BaseModel):
    explanation: str = Field(description="Plain-language explanation tied only to the supplied data.")
    recommended_followup: str = Field(description="A cautious, non-diagnostic next-step suggestion.")


@mcp.tool()
def generate_clinical_explanation(
    test_name: str,
    value: float,
    unit: str,
    severity: Literal["Critical", "Warning", "Normal"],
    reason: str,
    min_reference: float,
    max_reference: float,
) -> dict:
    """Generate a structured, cautious explanation using Gemini."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    prompt = f"""
You are the explanation component of a clinical lab demo application.
Do not diagnose disease. Do not invent symptoms, causes, or treatment.
Use only the supplied laboratory facts. Explain what the flag means in plain language.
If normal, reassure without claiming the patient is healthy.
If warning/critical, state that clinical interpretation depends on the patient's context
and that the result should be reviewed by an appropriate healthcare professional.
Return concise text suitable for a UI.

Test: {test_name}
Result: {value} {unit}
Reference interval: {min_reference} - {max_reference} {unit}
Severity: {severity}
Reason: {reason}
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": Explanation,
            "temperature": 0.2,
        },
    )

    parsed = response.parsed
    if parsed is None:
        parsed = Explanation.model_validate_json(response.text)

    return {
        "explanation": parsed.explanation,
        "recommended_followup": parsed.recommended_followup,
    }


app = mcp.streamable_http_app()
