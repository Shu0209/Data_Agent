from data_agent.models.schemas import AgentSchema
from data_agent.utils.llm import choose_llm
from langchain_core.messages import AIMessage, HumanMessage




def curate_question_node(state:AgentSchema)->AgentSchema:
     user_question=state.user_input

     llm=choose_llm('low')


     prompt=f"""
Rewrite the user's question to make it clear and grammatically correct.
Preserve the original meaning.
Do not answer the question or add assumptions.
Return only the rewritten question.

User question: {user_question}
"""

     response=llm.invoke(prompt)

     curated_question = response.content.strip()
     state.curated_ques=curated_question


     state.messages=state.messages + [HumanMessage(content=curated_question)]


     return state