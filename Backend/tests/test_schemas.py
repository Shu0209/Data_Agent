import pytest
from pydantic import ValidationError
from data_agent.models.schemas import AgentSchema, JudgeSchema
from data_agent.main import QueryRequest


def test_query_request_valid():
    """Valid user question should create request object successfully."""
    req = QueryRequest(user_input="How many rides occurred yesterday?")
    assert req.user_input == "How many rides occurred yesterday?"
    assert req.thread_id == "default_user"


def test_query_request_custom_thread_id():
    """QueryRequest should accept custom thread_id."""
    req = QueryRequest(user_input="Show all payments", thread_id="thread-123")
    assert req.thread_id == "thread-123"


def test_query_request_empty_input_fails():
    """Empty question must be rejected by min_length validation."""
    with pytest.raises(ValidationError):
        QueryRequest(user_input="")


def test_judge_schema_valid():
    """JudgeSchema should properly parse valid safety evaluations."""
    judge = JudgeSchema(answer="Yes", comments="Safe read-only query.")
    assert judge.answer == "Yes"
    assert "Safe" in judge.comments


def test_agent_schema_defaults():
    """AgentSchema should initialize with proper types and allow field assignment."""
    state = AgentSchema(
        user_input="Find vehicles",
        curated_ques="Find drivers",
        is_safe="Yes",
        generated_sql_query="SELECT * FROM vehicles;",
        sql_query_execution_result="[(1, 'Toyota')]",
        final_answer="Found 1 vehicle.",
    )
    assert state.user_input == "Find vehicles"
    assert state.is_safe == "Yes"
    assert state.generated_sql_query == "SELECT * FROM vehicles;"
    assert state.final_answer == "Found 1 vehicle."
