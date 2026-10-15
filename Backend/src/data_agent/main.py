from dotenv import load_dotenv
from fastapi import FastAPI, Response
from pydantic import BaseModel, Field
from typing import Optional 
from data_agent.agents import ai_data_agent

import logging


load_dotenv()

logger = logging.getLogger(__name__)



app=FastAPI(title="Database Agent")




class QueryRequest(BaseModel):
    user_input:str=Field(
        ...,
        min_length=1,
        description="Question to ask the Database Agent",
    )
    thread_id:Optional[str]="default_user"





@app.get("/")
def home():
    return {"message": "DataBase Agent Backend is Live."}

@app.get("/graph_img")
def get_graph_image():
    try:
        graph_image = ai_data_agent.get_graph().draw_mermaid_png()
        return Response(content=graph_image, media_type="image/png")

    except Exception as e:
        logger.exception(f"Could not generate graph image: {e}")


@app.post("/query")
def query(request: QueryRequest):

    user_input=request.user_input
    thread_id=request.thread_id

    state = {
            "messages": [],
            "user_input": user_input,
            "curated_ques": "",
            "prompt_query_context": "",
            "generated_sql_query": "",
            "is_safe": "No",
            "comments": "",
            "sql_query_execution_result": "",
            "final_answer": ""
        }

    config = {"configurable": {"thread_id": thread_id}}


    try:
        final_output=ai_data_agent.invoke(state,config=config)

        return{
            "curated_ques": final_output.get("curated_ques"),
            "prompt_query_context": final_output.get("prompt_query_context"),
            "generated_sql_query": final_output.get("generated_sql_query"),
            "is_safe": final_output.get("is_safe"),
            "comments": final_output.get("comments"),
            "sql_query_execution_result": final_output.get("sql_query_execution_result"),
            "final_answer": final_output.get("final_answer")
        }

    except Exception as e:
        return{
                    "messages": final_output.get("messages"),
                    "user_input": user_input,
                    "curated_ques": "",
                    "prompt_query_context": "",
                    "generated_sql_query": "",
                    "is_safe": "",
                    "comments": "",
                    "sql_query_execution_result": "",
                    "final_answer": "I apologize, but I encountered an internal error while processing your request. Please try again later.",
                    "thought_process": ["Error encountered during execution."]
                }



