from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .agent import ClinicalLabAgent
from .config import get_settings
from .models import AnalyzeRequest, AnalyzeResponse

settings = get_settings()
app = FastAPI(
    title="Clinical Lab Results Analyzer",
    version="1.0.0",
    description="Explainable AI lab-result analyzer using FastAPI, MCP and Gemini.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = ClinicalLabAgent()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze_labs", response_model=AnalyzeResponse)
async def analyze_labs(request: AnalyzeRequest):
    try:
        results = await agent.analyze(request.labs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Agent/MCP/LLM processing failed: {exc}",
        ) from exc

    summary = {
        "critical": sum(r.severity == "Critical" for r in results),
        "warning": sum(r.severity == "Warning" for r in results),
        "normal": sum(r.severity == "Normal" for r in results),
    }
    return AnalyzeResponse(results=results, summary=summary)
