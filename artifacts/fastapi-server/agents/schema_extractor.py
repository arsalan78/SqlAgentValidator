"""
AGENT 1 — Schema Extractor (HANA-aware)

Priority order:
  1. If a live HANA connection is available → introspect SYS.TABLES / SYS.TABLE_COLUMNS
     so the agent works with the REAL schema (no static registry needed).
  2. Fall back to the static table_registry.py if HANA is unreachable.

The LLM then picks the relevant subset of tables from whatever schema it received.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from state import AgentState

try:
    from hana_connection import get_schema_from_hana
    HANA_AVAILABLE = True
except Exception:
    HANA_AVAILABLE = False

from table_registry import (
    get_all_table_summaries,
    find_tables_by_names,
    get_table_schema_ddl,
    TABLE_REGISTRY,
    TableDefinition,
    ColumnDefinition,
)


def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-5.2",
        temperature=0,
        base_url=os.environ["AI_INTEGRATIONS_OPENAI_BASE_URL"],
        api_key=os.environ["AI_INTEGRATIONS_OPENAI_API_KEY"],
    )


def _hana_tables_to_registry(raw: list) -> list[TableDefinition]:
    """Convert get_schema_from_hana() output to TableDefinition objects."""
    result = []
    for t in raw:
        if "error" in t:
            continue
        cols = [
            ColumnDefinition(
                name=c["name"],
                type=c["type"],
                description=c.get("description", ""),
                primary_key=c.get("primary_key", False),
                nullable=c.get("nullable", True),
            )
            for c in t.get("columns", [])
        ]
        schema = t["schema"]
        table_name = t["table_name"]
        result.append(
            TableDefinition(
                schema=schema,
                table_name=table_name,
                full_name=t.get("full_name", f"{schema}.{table_name}"),
                description=t.get("description", f"Table {schema}.{table_name}"),
                columns=cols,
            )
        )
    return result


def _build_summaries(tables: list[TableDefinition]) -> str:
    lines = []
    for t in tables:
        col_names = ", ".join(c.name for c in t.columns[:8])
        suffix = f" (+{len(t.columns)-8} more)" if len(t.columns) > 8 else ""
        lines.append(f"- {t.full_name}: {t.description} | Columns: {col_names}{suffix}")
    return "\n".join(lines)


def schema_extractor_agent(state: AgentState) -> AgentState:
    llm = build_llm()
    log_prefix = f'[SchemaExtractor] Analyzing query: "{state["user_query"]}"'
    new_log = list(state["agent_log"]) + [log_prefix]

    # ── Try to get live schema from HANA ────────────────────────────────────
    all_tables = TABLE_REGISTRY
    source = "static registry"

    if HANA_AVAILABLE and os.environ.get("HANA_HOST"):
        new_log.append("[SchemaExtractor] Fetching live schema from HANA...")
        try:
            raw = get_schema_from_hana()
            if raw and "error" not in raw[0]:
                converted = _hana_tables_to_registry(raw)
                if converted:
                    all_tables = converted
                    source = f"live HANA ({len(converted)} tables)"
                else:
                    new_log.append("[SchemaExtractor] HANA returned 0 tables — using static registry")
            else:
                err = raw[0].get("error", "unknown") if raw else "empty response"
                new_log.append(f"[SchemaExtractor] HANA schema fetch failed: {err} — using static registry")
        except Exception as e:
            new_log.append(f"[SchemaExtractor] HANA connection error: {e} — using static registry")

    new_log.append(f"[SchemaExtractor] Schema source: {source} ({len(all_tables)} tables available)")

    summaries = _build_summaries(all_tables)

    system_prompt = f"""You are a SAP HANA database schema expert.
Given a user question, identify the EXACT table names (in SCHEMA.TABLE format) needed to answer it.

Available tables:
{summaries}

Rules:
- Only list tables directly needed for the query.
- Include all tables required for JOINs.
- Respond with ONLY a JSON array of full table names, e.g.: ["SALES.ORDERS", "SALES.CUSTOMERS"]
- No explanations, just the JSON array."""

    user_prompt = (
        f'User question: "{state["user_query"]}"\n\n'
        f"Which tables are needed? Return only a JSON array of full table names."
    )

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        content = str(response.content).strip()
        match = re.search(r'\[.*?\]', content, re.DOTALL)
        if not match:
            raise ValueError(f"Could not parse table list: {content}")

        table_names = json.loads(match.group(0))

        # Find matching tables from whatever source we used
        relevant = [t for t in all_tables if t.full_name in table_names]
        if not relevant:
            relevant = all_tables[:5]  # sensible fallback

        schema_context = get_table_schema_ddl(relevant)

        return {
            **state,
            "relevant_tables": relevant,
            "schema_context": schema_context,
            "agent_log": new_log + [
                f"[SchemaExtractor] Identified tables: {', '.join(t.full_name for t in relevant)}",
            ],
        }

    except Exception as e:
        return {
            **state,
            "error": f"SchemaExtractor failed: {e}",
            "agent_log": new_log + [f"[SchemaExtractor] ERROR: {e}"],
        }
