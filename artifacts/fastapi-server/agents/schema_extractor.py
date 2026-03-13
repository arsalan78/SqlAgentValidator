"""
AGENT 1 — Schema Extractor
Reads the user query and identifies relevant HANA tables from the registry.
"""

import json
import os
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from table_registry import get_all_table_summaries, find_tables_by_names, get_table_schema_ddl, TABLE_REGISTRY
from state import AgentState


def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-5.2",
        temperature=0,
        base_url=os.environ["AI_INTEGRATIONS_OPENAI_BASE_URL"],
        api_key=os.environ["AI_INTEGRATIONS_OPENAI_API_KEY"],
    )


def schema_extractor_agent(state: AgentState) -> AgentState:
    llm = build_llm()
    all_summaries = get_all_table_summaries()
    log_prefix = f'[SchemaExtractor] Analyzing query: "{state["user_query"]}"'

    system_prompt = f"""You are a SAP HANA database schema expert.
Given a user question, identify the EXACT table names (in SCHEMA.TABLE format) needed to answer the question.

Available tables:
{all_summaries}

Rules:
- Only list tables that are DIRECTLY needed to answer the question.
- If multiple tables are needed for a JOIN, include all of them.
- Respond with ONLY a JSON array of full table names, e.g.: ["SALES.ORDERS", "SALES.CUSTOMERS"]
- Do NOT include explanations, just the JSON array."""

    user_prompt = f'User question: "{state["user_query"]}"\n\nWhich tables are needed? Return only a JSON array of full table names.'

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        content = str(response.content).strip()
        match = re.search(r'\[.*?\]', content, re.DOTALL)
        if not match:
            raise ValueError(f"Could not parse table list from LLM response: {content}")

        table_names = json.loads(match.group(0))
        relevant_tables = find_tables_by_names(table_names)

        if not relevant_tables:
            relevant_tables = TABLE_REGISTRY

        schema_context = get_table_schema_ddl(relevant_tables)

        return {
            **state,
            "relevant_tables": relevant_tables,
            "schema_context": schema_context,
            "agent_log": state["agent_log"] + [
                log_prefix,
                f"[SchemaExtractor] Identified tables: {', '.join(t.full_name for t in relevant_tables)}",
            ],
        }

    except Exception as e:
        return {
            **state,
            "error": f"SchemaExtractor failed: {e}",
            "agent_log": state["agent_log"] + [log_prefix, f"[SchemaExtractor] ERROR: {e}"],
        }
