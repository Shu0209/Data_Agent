from data_agent.models.schemas import AgentSchema
from data_agent.utils.schema_catalog import build_schema_context


def schema_context_node(state: AgentSchema) -> AgentSchema:
    """Attach the (cached, question-scoped) schema to state.

    The schema is stored on its own. The SQL prompt is assembled in generate_sql,
    so the prompt text itself is never kept in state or returned by the API.
    """
    question = state.curated_ques or state.user_input

    schema_context, schema_tables = build_schema_context(question)

    state.schema_context = schema_context
    state.schema_tables = schema_tables

    return state
