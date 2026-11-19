import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from qdrant_client import QdrantClient

from erp import match_contract
from rag import analyze_email, search_knowledge
from schemas import EmailRequest, SearchRequest
from workflow import build_workflow


logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.qdrant = QdrantClient(
        url=os.environ["QDRANT_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
        timeout=10,
    )

    try:
        yield
    finally:
        app.state.qdrant.close()


app = FastAPI(
    title="Inovidus Demo",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/qdrant")
def qdrant_health(request: Request):
    try:
        request.app.state.qdrant.get_collections()

    except Exception:
        logger.exception("Qdrant connection check failed")

        raise HTTPException(
            status_code=503,
            detail="Qdrant connection failed. Check the backend logs.",
        ) from None

    return {
        "status": "ok",
        "service": "qdrant",
    }


@app.post("/knowledge/search")
def knowledge_search(data: SearchRequest, request: Request):
    try:
        matches = search_knowledge(
            client=request.app.state.qdrant,
            text=data.text,
            limit=data.limit,
        )

    except Exception:
        logger.exception("Semantic search failed")

        raise HTTPException(
            status_code=503,
            detail="Semantic search failed. Check the backend logs.",
        ) from None

    return {
        "query": data.text,
        "matches": matches,
    }


@app.post("/reports/analyze")
def reports_analyze(data: EmailRequest, request: Request):
    try:
        result = analyze_email(
            client=request.app.state.qdrant,
            subject=data.subject,
            body=data.body,
        )

        report = result["report"]

        erp_match = match_contract(
            tenant_name=report["tenant_name"],
            address=report["address"],
            unit_description=report["unit_description"],
        )

        result["erp_match"] = erp_match

        result["workflow"] = build_workflow(
            report=report,
            erp_match=erp_match,
            subject=data.subject,
        )

    except ValueError:
        logger.exception("Report validation failed")

        raise HTTPException(
            status_code=502,
            detail="Report validation failed. Check the backend logs.",
        ) from None

    except Exception:
        logger.exception("Report processing failed")

        raise HTTPException(
            status_code=503,
            detail="Report processing failed. Check the backend logs.",
        ) from None

    return result