from data_agent.models.schemas import AgentSchema
from data_agent.utils.llm import choose_llm
from langchain_core.messages import AIMessage, HumanMessage
import logfire

_MAX_CONTEXT_MESSAGES = 6

def _format_recent_history(messages: list) -> str:
    """Format the most recent user/assistant turns for follow-up disambiguation."""
    recent = [
        m for m in messages[-_MAX_CONTEXT_MESSAGES:] if isinstance(m, (HumanMessage, AIMessage))
    ]
    if not recent:
        return "None"

    lines = []
    for msg in recent:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        content = str(msg.content).strip()
        if len(content) > 400:
            content = content[:400] + "..."
        lines.append(f"{role}: {content}")
    return "\n".join(lines)





def curate_question_node(state: AgentSchema) -> dict:
    with logfire.span("🟢Curate question Node Activated"):
        user_question = state.user_input

        llm = choose_llm("low")

        history_block = _format_recent_history(state.messages)

        prompt = f"""
    Rewrite the user's latest question into a clear, grammatically correct, standalone database question.
    If the latest question is a follow-up (for example using "that", "those", "it", or "break down by..."), resolve references using the conversation history below.
    Preserve the original meaning without answering the question or inventing columns/values.
    Return only the rewritten question.

    Conversation history:
    {history_block}

    Latest user question: {user_question}
    """

        response = llm.invoke(prompt)
        logfire.info("✅Question curation completed successfully")

        return {
            "curated_ques": response.content.strip(),
            "messages": [HumanMessage(content=user_question)],
        }
