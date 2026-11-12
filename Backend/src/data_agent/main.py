from data_agent.config import settings
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from dotenv import load_dotenv
from fastapi import FastAPI, Response, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
from data_agent.guardrails.rails import (
    get_rails,
    async_check_guardrails,
)
from data_agent.agents.graph import ai_data_agent
from data_agent.utils.database import check_database_health

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded



import os
import logfire


load_dotenv()

logfire.configure(token=os.getenv("LOGFIRE_API_KEY"))




@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eagerly initialize and warm up NeMo Guardrails and DB schema on startup."""
    logfire.info("Starting Database Agent Application")
    try:
        with logfire.span("Nemo Guardrails Startup"):
            rails = get_rails()
            await rails.generate_async(messages=[{"role": "user", "content": "hello"}])
        logfire.info("✅NeMo Guardrails Startup completed")
    except Exception as e:
        logfire.error(
            "❌NeMo Guardrails Startup failed: {error_type}",
            error_type=type(e).__name__,
        )

    try:
        with logfire.span("Database schema catalog warmup"):
            from data_agent.utils.schema_catalog import build_schema_context

            build_schema_context("warmup")
        logfire.info("✅Database schema catalog cache pre-warmed successfully.")
    except Exception as e:
        logfire.error(
            "❌Schema catalog warmup failed: {error_type}",
            error_type=type(e).__name__,
        )
    logfire.info("✅Data Agent application startup completed")

    yield

    logfire.info("Data Agent application shutting down")


app = FastAPI(title="Database Agent", lifespan=lifespan)

logfire.instrument_fastapi(app)


limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

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
    logfire.info("Home endpoint accessed")

    return {"message": "DataBase Agent Backend is Live."}


@app.get("/health")
def health_check():
    """Readiness check verifying PostgreSQL connectivity."""
    with logfire.span("Database health check"):

        db_ok, db_status = check_database_health()

        payload = {
            "status": "healthy" if db_ok else "degraded",
            "database": db_status,
        }

        if db_ok:
            logfire.info("✅Database health check successful")
        else:
            logfire.warning(
                "❌Database health check failed: {database_status}",
                database_status=db_status,
            )

        code = (
            status.HTTP_200_OK
            if db_ok
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return JSONResponse(
            status_code=code,
            content=payload,
        )


@app.get("/graph_img")
def get_graph_image():
    try:
        with logfire.span("Generate LangGraph visualization"):
            graph_image = ai_data_agent.get_graph().draw_mermaid_png()

        logfire.info("LangGraph visualization generated")

        return Response(
            content=graph_image,
            media_type="image/png",
        )

    except Exception as e:
        logfire.error(
            "❌Graph visualization failed: {error_type}",
            error_type=type(e).__name__,
        )

        return Response(
            content="Could not generate graph image",
            status_code=500,
        )


@app.post("/guardrail")
async def guardrail_check(query_data: QueryRequest):
    """Directly evaluate user input against NeMo Guardrails."""
    return await async_check_guardrails(query_data.user_input)


@app.post("/query")
@limiter.limit("6/minute")
async def query(request: Request, query_data: QueryRequest):

    user_input = query_data.user_input
    thread_id = query_data.thread_id

    logfire.info("Database Agent Input received")

    # 1. Guardrail input validation
    try:
        with logfire.span("NeMo Guardrails input validation"):
            guardrail_result = await async_check_guardrails(user_input)
        
        if not guardrail_result.get("is_allowed", False):
            logfire.warning(
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
        
        logfire.info("✅Guardrails validation passed")
    except Exception as e:
        logfire.error(f"❌Guardrail check failed: {e}")

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
        with logfire.span("LangGraph Data Agent execution",thread_id=thread_id,):
            final_output = await ai_data_agent.ainvoke(state, config=config)

        logfire.info("✅LangGraph execution completed successfully")

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
        logfire.error(f"❌Error during agent execution: {e}")
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
