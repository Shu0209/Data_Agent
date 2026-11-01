from data_agent.models.schemas import AgentSchema
from langchain_core.messages import HumanMessage, AIMessage


def canceled_sql_node(state: AgentSchema) -> AgentSchema:
    comments = state.comments

    state.final_answer = f"The generated SQL query was deemed unsafe to execute. The reason provided by the judge is {comments}. Therefore, the SQL query will not be executed."

    state.messages = state.messages + [AIMessage(content=f"{state.final_answer}")]

    return state
