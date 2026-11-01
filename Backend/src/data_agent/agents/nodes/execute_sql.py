from data_agent.models.schemas import AgentSchema
from data_agent.config import settings
from data_agent.utils.database import DatabaseClass


def execute_sql_node(state: AgentSchema) -> AgentSchema:
    sql_query = state.generated_sql_query

    conn_details = {
        "host": settings.DB_host,
        "port": settings.DB_port,
        "user": settings.DB_user,
        "password": settings.DB_password,
        "dbname": settings.DB_name,
    }

    obj = DatabaseClass(conn_details)

    execution_result = obj.execute_query(sql_query)

    state.sql_query_execution_result = execution_result

    return state
