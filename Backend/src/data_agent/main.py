from data_agent.config import settings
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from dotenv import load_dotenv
from fastapi import FastAPI, Response, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
from data_agent.guardrails.rails import check_guardrails, get_rails,async_check_guardrails
from data_agent.agents.graph import ai_data_agent
from data_agent.utils.database import check_database_health

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


import logging
import os


load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eagerly initialize and warm up NeMo Guardrails and DB schema on startup."""
    logger.info("Initializing and warming up NeMo Guardrails on startup...")
    try:
        rails = get_rails()
        rails.generate(messages=[{"role": "user", "content": "hello"}])
        logger.info("NeMo Guardrails warmup completed successfully.")
    except Exception as e:
        logger.warning(f"NeMo Guardrails warmup skipped or encountered an issue: {e}")

    try:
        from data_agent.utils.schema_catalog import build_schema_context
        build_schema_context("warmup")
        logger.info("Database schema catalog cache pre-warmed successfully.")
    except Exception as e:
        logger.warning(f"Database schema catalog warmup skipped or encountered an issue: {e}")

    yield


app = FastAPI(title="Database Agent", lifespan=lifespan)

limiter=Limiter(key_func=get_remote_address)
app.state.limiter=limiter

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)





app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)






class QueryRequest(BaseModel):
    user_input: str = Field(
        ...,
        min_length=1,
        description="Question to ask the Database Agent",
    )
    thread_id: Optional[str] = "default_user"


@app.get("/")
def home():
    return {"message": "DataBase Agent Backend is Live."}


@app.get("/health")
def health_check():
    """Readiness check verifying PostgreSQL connectivity."""
    db_ok, db_status = check_database_health()
    payload = {
        "status": "healthy" if db_ok else "degraded",
        "database": db_status,
    }
    code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content=payload)

@app.get("/graph_img")
def get_graph_image():
    try:
        graph_image = ai_data_agent.get_graph().draw_mermaid_png()
        return Response(content=graph_image, media_type="image/png")

    except Exception as e:
        logger.exception(f"Could not generate graph image: {e}")
        return Response(content="Could not generate graph image", status_code=500)


@app.post("/guardrail")
async def guardrail_check(query_data: QueryRequest):
    """Directly evaluate user input against NeMo Guardrails."""
    return await async_check_guardrails(query_data.user_input)


@app.post("/query")
@limiter.limit("6/minute")
async def query(request:Request ,query_data: QueryRequest):

    user_input = query_data.user_input
    thread_id = query_data.thread_id

    # 1. Guardrail input validation
    try:
        guardrail_result = await async_check_guardrails(user_input)
        if not guardrail_result.get("is_allowed", False):
            logger.info(
                f"Guardrail intercepted query: flagged={guardrail_result.get('flagged')}, "
                f"reason={guardrail_result.get('reason')}"
            )
            return {
                "curated_ques": user_input,
                "schema_tables": [],
                "generated_sql_query": "",
                "is_safe": "No" if guardrail_result.get("flagged") else "Yes",
                "comments": guardrail_result.get("reason", "Handled by Guardrails"),
                "sql_query_execution_result": "",
                "final_answer": guardrail_result.get("bot_response", ""),
            }
    except Exception as e:
        logger.exception(f"Guardrail check failed: {e}")

    # 2. Proceed with Agent LangGraph workflow if input conforms to guardrails
    state = {
        "messages": [],
        "user_input": user_input,
        "curated_ques": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": "",
    }

    config = {"configurable": {"thread_id": thread_id}}

    try:
        final_output =await ai_data_agent.ainvoke(state, config=config)

        return {
            "curated_ques": final_output.get("curated_ques"),
            "prompt_query_context": final_output.get("prompt_query_context"),
            "generated_sql_query": final_output.get("generated_sql_query"),
            "is_safe": final_output.get("is_safe"),
            "comments": final_output.get("comments"),
            "sql_query_execution_result": final_output.get(
                "sql_query_execution_result"
            ),
            "final_answer": final_output.get("final_answer"),
        }

    except Exception as e:
        logger.exception(f"Error during agent execution: {e}")
        return {
            "user_input": user_input,
            "curated_ques": "",
            "prompt_query_context": "",
            "generated_sql_query": "",
            "is_safe": "No",
            "comments": f"Internal error during execution: {e}",
            "sql_query_execution_result": "",
            "final_answer": "I apologize, but I encountered an internal error while processing your request. Please try again later.",
        }



def main() -> None:
   
    import uvicorn

    uvicorn.run("data_agent.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()

