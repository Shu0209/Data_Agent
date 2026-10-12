from data_agent.utils.llm import choose_llm

from data_agent.Models.schemas import AgentSchema


def curate_question(state:AgentSchema)->AgentSchema:
     user_question=state.user_input

     llm=choose_llm('low')

     response=llm.invoke(f"Curate the followinng question: {user_question}")

     state.curated_ques=response.content
     return state

