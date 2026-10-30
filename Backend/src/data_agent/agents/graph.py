from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from data_agent.models.schemas import AgentSchema
from data_agent.agents.nodes.curate_question import curate_question_node
# from data_agent.agents.nodes.prompt_query_context import prompt_query_context_node
from data_agent.agents.nodes.schema_context import schema_context_node
from data_agent.agents.nodes.generate_sql import generate_sql_node
from data_agent.agents.nodes.judge import judge_node
from data_agent.agents.nodes.execute_sql import execute_sql_node
from data_agent.agents.nodes.final_answer import final_answer_node
from data_agent.agents.nodes.cancel_sql import canceled_sql_node


graph=StateGraph(AgentSchema)

graph.add_node("curate_ques",curate_question_node)

graph.add_node("schema_context",schema_context_node)

graph.add_node("generate_sql",generate_sql_node)

graph.add_node("judge",judge_node)

graph.add_node("canceled_sql",canceled_sql_node)

graph.add_node("execute_sql",execute_sql_node)

graph.add_node("final_answer",final_answer_node)




graph.add_edge(START,"curate_ques")
graph.add_edge("curate_ques","schema_context")
graph.add_edge("schema_context","generate_sql")
graph.add_edge("generate_sql","judge")

def guard_edge(state:AgentSchema)->str:
    is_safe=state.is_safe

    if is_safe.lower()=="yes":
        return "execute_sql"
    else:
        return "canceled_sql"


graph.add_conditional_edges("judge",guard_edge,{
        "execute_sql":"execute_sql",
        "canceled_sql":"canceled_sql"
    })


graph.add_edge("canceled_sql",END)

graph.add_edge("execute_sql","final_answer")

graph.add_edge("final_answer",END)


checkpointer=MemorySaver()

ai_data_agent = graph.compile(checkpointer=checkpointer)



