import logfire

from data_agent.models.schemas import AgentSchema
from data_agent.utils.schema_catalog import build_schema_context





def schema_context_node(state: AgentSchema) -> AgentSchema:
    """Attach cached, question-scoped schema context to graph state."""

    with logfire.span("Schema Context Node"):

        try:
            question = state.curated_ques or state.user_input

            logfire.info("Schema context retrieval started")

            # Retrieve relevant schema
            with logfire.span("Build Database Schema Context"):

                schema_context, schema_tables = build_schema_context(
                    question
                )

            # Attach schema to state
            state.schema_context = schema_context
            state.schema_tables = schema_tables

            logfire.info(
                "✅Schema context retrieval completed")

            return state

        except Exception as e:
            logfire.error(f"❌Schema context retrieval failed: {e}")

            raise
