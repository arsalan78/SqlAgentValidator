"""
AGENT 3 — SQL Validator (HANA-aware)

Two-stage validation:
  Stage 1: Execute the SQL against the real HANA database.
           If it runs without error → PASSED immediately (ground truth).
           If HANA returns an error → feed the exact error to Stage 2.
  Stage 2: LLM review for semantic correctness and dialect rules.
           Uses the real HANA execution result (or error) as additional context.

This approach replaces pure LLM guessing with actual database feedback.
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
    from hana_connection import execute_query, test_connection
    HANA_AVAILABLE = True
except Exception:
    HANA_AVAILABLE = False


def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-5.2",
        temperature=0,
        base_url=os.environ["AI_INTEGRATIONS_OPENAI_BASE_URL"],
        api_key=os.environ["AI_INTEGRATIONS_OPENAI_API_KEY"],
    )


def _try_hana_execution(sql: str) -> dict:
    """
    Attempt to execute the SQL on the real HANA instance.
    Returns: {executed: bool, error: str|None, row_count: int, sample_cols: list}
    """
    if not HANA_AVAILABLE:
        return {"executed": False, "error": "hdbcli not installed", "row_count": 0, "sample_cols": []}

    hana_host = os.environ.get("HANA_HOST", "")
    if not hana_host or hana_host.startswith("dummy"):
        return {"executed": False, "error": "HANA_HOST is not configured (using dummy credentials)", "row_count": 0, "sample_cols": []}

    result = execute_query(sql, max_rows=5)
    if result["error"]:
        return {"executed": True, "error": result["error"], "row_count": 0, "sample_cols": []}
    return {
        "executed": True,
        "error": None,
        "row_count": len(result["rows"]),
        "sample_cols": result["columns"],
    }


def sql_validator_agent(state: AgentState) -> AgentState:
    if state["error"]:
        return state

    llm = build_llm()
    log_prefix = f"[SQLValidator] Validating iteration {state['iteration']} SQL"
    new_log = list(state["agent_log"]) + [log_prefix]

    # ── Stage 1: Try real HANA execution ────────────────────────────────────
    hana_result = _try_hana_execution(state["generated_sql"])
    hana_context = ""

    if hana_result["executed"]:
        if hana_result["error"] is None:
            hana_context = (
                f"\n\nREAL HANA EXECUTION: SUCCESS — "
                f"returned {hana_result['row_count']} row(s), "
                f"columns: {hana_result['sample_cols']}"
            )
            new_log.append(
                f"[SQLValidator] HANA execution: SUCCESS ({hana_result['row_count']} rows)"
            )
        else:
            hana_context = (
                f"\n\nREAL HANA EXECUTION ERROR:\n{hana_result['error']}\n\n"
                f"The SQL FAILED on the actual database. "
                f"You must fix the exact error above."
            )
            new_log.append(
                f"[SQLValidator] HANA execution: FAILED — {hana_result['error']}"
            )
    else:
        new_log.append(
            f"[SQLValidator] HANA not available ({hana_result['error']}), using LLM validation only"
        )

    # ── If HANA ran it fine, skip LLM and PASS immediately ──────────────────
    if hana_result["executed"] and hana_result["error"] is None:
        new_log.append(
            "[SQLValidator] Result: PASSED ✓ — Confirmed by real HANA execution"
        )
        return {
            **state,
            "validation_passed": True,
            "validation_feedback": "",
            "final_sql": state["generated_sql"],
            "agent_log": new_log,
        }

    # ── Stage 2: LLM validation (with HANA error context if available) ──────
    system_prompt = f"""You are a senior SAP HANA database architect and SQL reviewer.

Validate the SQL query for:
1. SAP HANA dialect correctness
2. Semantic accuracy (does it answer the user's intent?)
3. Schema column/table existence
4. Performance best practices

SAP HANA dialect rules:
- Use TOP N not LIMIT N
- Always use SCHEMA.TABLE_NAME fully qualified
- Use NVARCHAR not VARCHAR
- Use COALESCE or IFNULL, not ISNULL
- DATE literals: DATE '2024-01-01'
- No BOOLEAN type, use TINYINT (0/1)
- No trailing semicolons in SELECT
- String concat: || operator

Available schema:
{state["schema_context"]}
{hana_context}

Respond with ONLY this JSON (no extra text):
{{
  "passed": true | false,
  "issues": ["issue 1", ...],
  "corrections": ["fix 1", ...],
  "summary": "one-sentence result"
}}"""

    user_prompt = (
        f'User question: "{state["user_query"]}"\n\n'
        f"SQL to validate:\n{state['generated_sql']}\n\n"
        "Return only the JSON."
    )

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        content = str(response.content).strip()
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if not match:
            raise ValueError(f"Could not parse JSON: {content}")

        result = json.loads(match.group(0))
        passed = result.get("passed") is True
        issues = result.get("issues", [])
        corrections = result.get("corrections", [])
        summary = result.get("summary", "")

        feedback = ""
        if not passed and issues:
            feedback = (
                "Issues found:\n"
                + "\n".join(f"  {i+1}. {issue}" for i, issue in enumerate(issues))
                + "\n\nRequired corrections:\n"
                + "\n".join(f"  {i+1}. {c}" for i, c in enumerate(corrections))
            )
            if hana_result["executed"] and hana_result["error"]:
                feedback = f"HANA execution error:\n  {hana_result['error']}\n\n" + feedback

        new_log += [
            f"[SQLValidator] Result: {'PASSED ✓' if passed else 'FAILED ✗'} — {summary}",
        ]
        if feedback:
            new_log.append(f"[SQLValidator] Feedback:\n{feedback}")

        return {
            **state,
            "validation_passed": passed,
            "validation_feedback": feedback,
            "final_sql": state["generated_sql"] if passed else "",
            "agent_log": new_log,
        }

    except Exception as e:
        return {
            **state,
            "error": f"SQLValidator failed: {e}",
            "agent_log": new_log + [f"[SQLValidator] ERROR: {e}"],
        }
