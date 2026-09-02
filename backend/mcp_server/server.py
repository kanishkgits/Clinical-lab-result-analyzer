import os
import re
from pathlib import Path
from typing import Literal

import pandas as pd
from dotenv import load_dotenv
from google import genai
from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field


# ============================================================
# PATHS AND ENVIRONMENT
# ============================================================

# server.py is located at:
# backend/mcp_server/server.py
#
# parents[1] therefore points to:
# backend/

BASE_DIR = Path(__file__).resolve().parents[1]

ENV_PATH = BASE_DIR / ".env"
DATASET_PATH = BASE_DIR / "data" / "lab_test_results_public.csv"

load_dotenv(ENV_PATH)

if not DATASET_PATH.exists():
    raise FileNotFoundError(
        f"Laboratory dataset not found at: {DATASET_PATH}"
    )

df = pd.read_csv(DATASET_PATH)


# Required columns from the Kaggle dataset
REQUIRED_COLUMNS = [
    "Test_Name",
    "Unit",
    "Reference_Range",
    "Min_Reference",
    "Max_Reference",
]

missing_columns = [
    column for column in REQUIRED_COLUMNS
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Dataset is missing required columns: {missing_columns}"
    )

mcp = MCPServer(
    "Clinical Lab Analyzer MCP",
    instructions=(
        "Tools for deterministic laboratory reference-range lookup "
        "and severity classification, plus LLM-generated explanations. "
        "The orchestrating agent must call these tools in order."
    ),
)

def normalize(name: str) -> str:
    """
    Normalize a laboratory test name for reliable matching.

    Example:
        '  Ferritin  ' -> 'ferritin'
        'Glikozile   Hemoglobin (HbA1c)' ->
        'glikozile hemoglobin (hba1c)'
    """

    return re.sub(r"\s+", " ", str(name).strip().lower())

@mcp.tool()
def reference_range_lookup(test_name: str) -> dict:
    """
    Look up the reference range for a laboratory test.

    The values are obtained directly from the supplied
    laboratory_test_results.csv dataset.

    Returns:
        test_name
        unit
        min_reference
        max_reference
        reference_range
    """

    if not test_name or not test_name.strip():
        raise ValueError("test_name cannot be empty")

    target = normalize(test_name)

    # Normalize dataset test names before comparison
    normalized_names = (
        df["Test_Name"]
        .astype(str)
        .map(normalize)
    )

    rows = df[normalized_names == target]

    if rows.empty:
        raise ValueError(
            f"Unknown laboratory test: {test_name}"
        )

    row = rows.iloc[0]

    return {
        "test_name": str(row["Test_Name"]),
        "unit": str(row["Unit"]),
        "min_reference": float(row["Min_Reference"]),
        "max_reference": float(row["Max_Reference"]),
        "reference_range": str(row["Reference_Range"]),
    }

@mcp.tool()
def classify_lab(
    value: float,
    min_reference: float,
    max_reference: float,
) -> dict:
    """
    Classify a laboratory result using a transparent severity policy.

    Classification:

    Normal:
        value is inside the reference interval.

    Warning:
        value is outside the reference interval but does not
        cross the critical threshold.

    Critical:
        value is below 50% of the lower reference limit or
        above 150% of the upper reference limit.

    This is an assignment/demo heuristic and is NOT a clinical
    decision rule.
    """

    if min_reference > max_reference:
        raise ValueError(
            "min_reference must be less than or equal to "
            "max_reference"
        )

    if min_reference <= value <= max_reference:

        return {
            "severity": "Normal",
            "reason": (
                "The result is inside the supplied "
                "reference interval."
            ),
            "route_order": 3,
        }

    if value < min_reference:

        critical = (
            min_reference > 0
            and value < (0.5 * min_reference)
        )

        severity = "Critical" if critical else "Warning"

        reason = (
            f"The result is below the lower reference "
            f"limit ({min_reference})."
        )

    else:

        critical = value > (1.5 * max_reference)

        severity = "Critical" if critical else "Warning"

        reason = (
            f"The result is above the upper reference "
            f"limit ({max_reference})."
        )

    return {
        "severity": severity,
        "reason": reason,
        "route_order": (
            1 if severity == "Critical" else 2
        ),
    }

class Explanation(BaseModel):
    explanation: str = Field(
        description=(
            "Plain-language explanation tied only to "
            "the supplied laboratory data."
        )
    )

    recommended_followup: str = Field(
        description=(
            "A cautious, non-diagnostic next-step suggestion."
        )
    )

@mcp.tool()
def generate_clinical_explanation(
    test_name: str,
    value: float,
    unit: str,
    severity: Literal[
        "Critical",
        "Warning",
        "Normal",
    ],
    reason: str,
    min_reference: float,
    max_reference: float,
) -> dict:
    """
    Generate a concise, cautious explanation of a laboratory
    result using Gemini.

    The LLM is only responsible for explaining the already
    determined classification. It does not determine severity.
    """

    api_key = os.getenv("GEMINI_API_KEY", "")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured"
        )

    model = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.5-flash-lite",
    )

    client = genai.Client(
        api_key=api_key
    )

    prompt = f"""
You are the explanation component of a clinical laboratory
results demo application.

Your task is to explain an already-classified laboratory result.

IMPORTANT RULES:

1. Do not diagnose any disease.
2. Do not claim that the patient has a medical condition.
3. Do not invent symptoms.
4. Do not invent causes.
5. Do not recommend medications or treatment.
6. Use only the laboratory information supplied below.
7. Keep the explanation concise and understandable.
8. If the result is Normal, explain that it is within the
   supplied reference interval without claiming that the
   patient is completely healthy.
9. If the result is Warning or Critical, explain that the
   result is outside the supplied reference interval and
   should be reviewed by an appropriate healthcare professional.
10. The severity classification has already been determined
    by a deterministic rule. Do not change it.

LABORATORY INFORMATION:

Test name:
{test_name}

Result:
{value} {unit}

Reference interval:
{min_reference} - {max_reference} {unit}

Severity:
{severity}

Classification reason:
{reason}

Return a concise explanation suitable for displaying in a
web application.

Also provide a cautious recommended follow-up step.
"""


    # --------------------------------------------------------
    # Call Gemini
    # --------------------------------------------------------

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

        try:
            parsed = Explanation.model_validate_json(
                response.text
            )

        except Exception as exc:
            raise RuntimeError(
                "Gemini returned an invalid structured response"
            ) from exc

    return {
        "explanation": parsed.explanation,
        "recommended_followup": (
            parsed.recommended_followup
        ),
    }

app = mcp.streamable_http_app()