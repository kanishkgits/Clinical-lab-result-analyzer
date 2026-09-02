from .config import get_settings
from .mcp_client import MCPAgentClient
from .models import LabAnalysis, LabInput


class ClinicalLabAgent:
    """
    Orchestrates the laboratory analysis workflow through MCP.

    Workflow:
        1. Look up reference range
        2. Classify result
        3. Route based on severity
        4. Generate LLM explanation
    """

    def __init__(self):
        settings = get_settings()
        self.mcp = MCPAgentClient(settings.mcp_server_url)

    async def analyze_one(self, lab: LabInput) -> LabAnalysis:

        lookup = await self.mcp.call(
            "reference_range_lookup",
            {
                "test_name": lab.test_name,
            },
        )
        if not lookup:
            raise ValueError(
                f"Unknown lab test '{lab.test_name}'. "
                "Reference range could not be found in the dataset."
            )

        test_name = lookup["test_name"]
        expected_unit = lookup["unit"]

        min_reference = float(
            lookup["min_reference"]
        )

        max_reference = float(
            lookup["max_reference"]
        )

        reference_range = lookup["reference_range"]

        if (
            lab.unit.strip().lower()
            != expected_unit.strip().lower()
        ):
            raise ValueError(
                f"Unit mismatch for {lab.test_name}: "
                f"expected {expected_unit}, "
                f"received {lab.unit}."
            )

        classification = await self.mcp.call(
            "classify_lab",
            {
                "value": lab.value,
                "min_reference": min_reference,
                "max_reference": max_reference,
            },
        )

        if not classification:
            raise RuntimeError(
                f"MCP classification failed for "
                f"{lab.test_name}."
            )

        severity = classification["severity"]
        reason = classification["reason"]
        route_order = classification["route_order"]

        explanation = await self.mcp.call(
            "generate_clinical_explanation",
            {
                "test_name": test_name,
                "value": lab.value,
                "unit": expected_unit,
                "severity": severity,
                "reason": reason,
                "min_reference": min_reference,
                "max_reference": max_reference,
            },
        )

        if not explanation:
            raise RuntimeError(
                f"MCP explanation generation failed for "
                f"{lab.test_name}."
            )

        return LabAnalysis(
            test_name=test_name,
            value=lab.value,
            unit=expected_unit,
            reference_range=reference_range,
            min_reference=min_reference,
            max_reference=max_reference,
            severity=severity,
            route_order=route_order,
            reason=reason,
            explanation=explanation["explanation"],
            recommended_followup=(
                explanation["recommended_followup"]
            ),
            disclaimer=(
                "Demo decision-support output; not a "
                "diagnosis or substitute for professional "
                "medical advice."
            ),
        )

    async def analyze(
        self,
        labs: list[LabInput],
    ) -> list[LabAnalysis]:

        results = []

        for lab in labs:
            result = await self.analyze_one(lab)
            results.append(result)

        return sorted(
            results,
            key=lambda item: item.route_order,
        )