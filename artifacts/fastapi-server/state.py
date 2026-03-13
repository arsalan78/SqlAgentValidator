from typing import TypedDict, List, Any


class AgentState(TypedDict):
    user_query: str
    iteration: int
    max_iterations: int
    relevant_tables: List[Any]
    schema_context: str
    generated_sql: str
    validation_passed: bool
    validation_feedback: str
    final_sql: str
    error: str
    agent_log: List[str]


def make_initial_state(user_query: str, max_iterations: int = 5) -> AgentState:
    return AgentState(
        user_query=user_query,
        iteration=0,
        max_iterations=max_iterations,
        relevant_tables=[],
        schema_context="",
        generated_sql="",
        validation_passed=False,
        validation_feedback="",
        final_sql="",
        error="",
        agent_log=[],
    )
