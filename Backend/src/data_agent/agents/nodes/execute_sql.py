from data_agent.models.schemas import AgentSchema
from data_agent.config import settings
from data_agent.utils.database import DatabaseClass

import logfire


def execute_sql_node(state: AgentSchema) -> AgentSchema:

    with logfire.span("Instilize execute_sql node"):
        
        try:
            sql_query = state.generated_sql_query

            conn_details = {
                "host": settings.DB_host,
                "port": settings.DB_port,
                "user": settings.DB_user,
                "password": settings.DB_password,
                "dbname": settings.DB_name,
            }

            with logfire.span("Initialize Database Connection"):
                obj = DatabaseClass(conn_details)

            with logfire.span("Execute Read-Only SQL Query"):
                execution_result = obj.execute_query(sql_query)

            state.sql_query_execution_result = execution_result

            logfire.info("SQL query execution completed successfully")

            return state

        except Exception as e:
            logfire.error(f"SQL query execution failed:{e}")

            state.sql_query_execution_result = (
                "Unable to execute the SQL query. "
                "Please review the query or try again."
            )

            return state
