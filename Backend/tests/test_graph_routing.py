from data_agent.agents.graph import guard_edge
from data_agent.models.schemas import AgentSchema


def test_guard_edge_routes_to_execute_sql_when_safe():
    """When query is safe ('Yes'), guard_edge should return 'execute_sql'."""
    state = AgentSchema(user_input="Find users", is_safe="Yes")
    next_node = guard_edge(state)
    assert next_node == "execute_sql"


def test_guard_edge_routes_to_canceled_sql_when_unsafe():
    """When query is unsafe ('No'), guard_edge should return 'canceled_sql'."""
    state = AgentSchema(user_input="Drop table users", is_safe="No")
    next_node = guard_edge(state)
    assert next_node == "canceled_sql"
