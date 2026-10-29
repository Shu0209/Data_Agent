from data_agent.models.schemas import AgentSchema
from data_agent.utils.llm import choose_llm




def generate_sql_node(state: AgentSchema)->AgentSchema:
    

    llm=choose_llm("high")

    response = llm.invoke(state.prompt_query_context)


    state.generated_sql_query=response.content.strip()

    return state