from data_agent.Models.schemas import AgentSchema

state = AgentSchema(
    message=["User: Show me total sales"],
    curated_ques="What is the total sales?",
    prompt_query_context="The database contains a sales table with an amount column.",
    is_safe="Yes",
    generated_sql_query="SELECT SUM(amount) FROM sales;",
    sql_query_execution_result="125000",
    final_answer="The total sales are 125,000."
)

print(state)