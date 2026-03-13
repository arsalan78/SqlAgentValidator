from dataclasses import dataclass, field
from typing import List, Any


@dataclass
class AgentState:
    user_query: str
    iteration: int = 0
    max_iterations: int = 5
    relevant_tables: List[Any] = field(default_factory=list)
    schema_context: str = ""
    generated_sql: str = ""
    validation_passed: bool = False
    validation_feedback: str = ""
    final_sql: str = ""
    error: str = ""
    agent_log: List[str] = field(default_factory=list)
