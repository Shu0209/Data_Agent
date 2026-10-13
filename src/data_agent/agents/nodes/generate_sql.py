from data_agent.models.schemas import AgentSchema
from data_agent.utils.llm import choose_llm




def generate_sql_node(state: AgentSchema)->AgentSchema:
    prompt=state.prompt_query_context

    llm=choose_llm("high")

    generate_sql_query=llm.invoke(prompt).content


    state.generated_sql_query=generate_sql_query

    return state