"""
SQL AGENT GRAPH — LangGraph (Python) orchestration

Flow:
  extract_schema → generate_sql → validate_sql
                                       │
                         ┌─────────────┴─────────────┐
                         │ passed                    │ failed (iterations < max)
                         ▼                           ▼
                        END                   generate_sql (loop)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from langgraph.graph import StateGraph, END
from typing import Literal

from state import AgentState, make_initial_state
from agents.schema_extractor import schema_extractor_agent
from agents.sql_generator import sql_generator_agent
from agents.sql_validator import sql_validator_agent


def should_loop(state: AgentState) -> Literal["generate_sql", "__end__"]:
    if state["error"]:
        return END
    if state["validation_passed"]:
        return END
    if state["iteration"] >= state["max_iterations"]:
        return END
    return "generate_sql"


def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("extract_schema", schema_extractor_agent)
    builder.add_node("generate_sql", sql_generator_agent)
    builder.add_node("validate_sql", sql_validator_agent)

    builder.set_entry_point("extract_schema")
    builder.add_edge("extract_schema", "generate_sql")
    builder.add_edge("generate_sql", "validate_sql")
    builder.add_conditional_edges(
        "validate_sql",
        should_loop,
        {
            "generate_sql": "generate_sql",
            END: END,
        },
    )

    return builder.compile()


async def run_sql_agent(user_query: str, max_iterations: int = 5) -> dict:
    graph = build_graph()
    initial_state = make_initial_state(user_query, max_iterations)

    result: AgentState = await graph.ainvoke(initial_state)

    return {
        "sql": result["final_sql"] if result["validation_passed"] else result["generated_sql"],
        "passed": result["validation_passed"],
        "iterations": result["iteration"],
        "feedback": result["validation_feedback"] or None,
        "log": result["agent_log"],
        "error": result["error"] or None,
    }
