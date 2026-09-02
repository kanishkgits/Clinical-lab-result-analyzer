from .config import get_settings
from .mcp_client import MCPAgentClient
from .models import LabAnalysis, LabInput


class ClinicalLabAgent:
    """Orchestrates the required Classify -> Route -> Explain workflow through MCP."""

    def __init__(self):
        settings = get_settings()
        self.mcp = MCPAgentClient(settings.mcp_server_url)

    async def analyze_one(self, lab: LabInput) -> LabAnalysis:
        lookup = await self.mcp.call(
            "reference_range_lookup",
            {"test_name": lab.test_name},
        )

        if not lookup.get("found"):
            raise ValueError(
                f"Unknown lab test '{lab.test_name}'. Add its reference range before analysis."
            )

        expected_unit = lookup["unit"]
        if lab.unit.strip().lower() != expected_unit.strip().lower():
            raise ValueError(
                f"Unit mismatch for {lab.test_name}: expected {expected_unit}, received {lab.unit}."
            )

        classification = await self.mcp.call(
            "classify_lab",
            {
                "value": lab.value,
                "min_reference": lookup["min_reference"],
                "max_reference": lookup["max_reference"],
            },
        )

        explanation = await self.mcp.call(
            "generate_clinical_explanation",
            {
                "test_name": lab.test_name,
                "value": lab.value,
                "unit": lab.unit,
                "severity": classification["severity"],
                "reason": classification["reason"],
                "min_reference": lookup["min_reference"],
                "max_reference": lookup["max_reference"],
            },
        )

        return LabAnalysis(
            test_name=lab.test_name,
            value=lab.value,
            unit=lab.unit,
            reference_range=lookup["reference_range"],
            min_reference=lookup["min_reference"],
            max_reference=lookup["max_reference"],
            severity=classification["severity"],
            route_order=classification["route_order"],
            reason=classification["reason"],
            explanation=explanation["explanation"],
            recommended_followup=explanation["recommended_followup"],
            disclaimer="Demo decision-support output; not a diagnosis or substitute for professional medical advice.",
        )

    async def analyze(self, labs: list[LabInput]) -> list[LabAnalysis]:
        results = []
        for lab in labs:
            results.append(await self.analyze_one(lab))
        return sorted(results, key=lambda item: item.route_order)
