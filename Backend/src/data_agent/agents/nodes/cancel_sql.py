from data_agent.models.schemas import AgentSchema
from langchain_core.messages import HumanMessage, AIMessage

import logfire

def canceled_sql_node(state: AgentSchema) -> AgentSchema:
    
    with logfire.span("Cancel sql node instilized"):
        comments = state.comments

        state.final_answer = f"The generated SQL query was deemed unsafe to execute. The reason provided by the judge is {comments}. Therefore, the SQL query will not be executed."

        state.messages = state.messages + [AIMessage(content=f"{state.final_answer}")]

        logfire.warning("SQL execution canceled by security validation")

        return state
