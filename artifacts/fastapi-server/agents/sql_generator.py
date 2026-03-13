"""
AGENT 2 — SQL Generator
Generates SAP HANA-compatible SQL from the user query and schema context.
If previous validation feedback exists, it incorporates corrections.
"""

import os
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from state import AgentState

HANA_SQL_RULES = """SAP HANA SQL dialect rules you MUST follow:
1. Use TOP N instead of LIMIT N: SELECT TOP 10 * FROM TABLE (not LIMIT 10)
2. Always use fully qualified table names: SCHEMA.TABLE_NAME
3. Use NVARCHAR instead of VARCHAR for strings
4. Date literals use ISO format: DATE '2024-01-01'
5. String concatenation uses || operator: col1 || ' ' || col2
6. Use TO_DATE(), TO_TIMESTAMP() for casting
7. Aggregations are standard: SUM, COUNT, AVG, MIN, MAX
8. Window functions are supported: ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)
9. CASE WHEN ... THEN ... ELSE ... END is supported
10. Subqueries must be aliased: (SELECT ...) AS sub
11. No trailing semicolons needed in pure SELECT statements
12. ISNULL is not available — use COALESCE or IFNULL instead
13. For pagination: use ROW_NUMBER() OVER (...) or TOP with ORDER BY
14. Boolean: no BOOLEAN type, use TINYINT (0/1) e.g. IS_ACTIVE = 1"""


def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-5.2",
        temperature=0,
        base_url=os.environ["AI_INTEGRATIONS_OPENAI_BASE_URL"],
        api_key=os.environ["AI_INTEGRATIONS_OPENAI_API_KEY"],
    )


def sql_generator_agent(state: AgentState) -> AgentState:
    if state["error"]:
        return state

    llm = build_llm()
    iteration = state["iteration"] + 1
    log_prefix = f"[SQLGenerator] Iteration {iteration} — generating SQL"

    correction_section = ""
    if state["iteration"] > 0 and state["validation_feedback"]:
        correction_section = (
            f"\n\nPREVIOUS ATTEMPT FAILED — Validator feedback to fix:\n"
            f"{state['validation_feedback']}\n\n"
            f"Previous SQL:\n{state['generated_sql']}\n\n"
            f"Please fix ALL the issues mentioned above."
        )

    system_prompt = f"""You are an expert SAP HANA SQL developer.
Generate a correct, efficient SQL query for SAP HANA that answers the user's question.

{HANA_SQL_RULES}

Available schema:
{state["schema_context"]}

Rules for your response:
- Output ONLY the SQL query, no explanations, no markdown code fences, no comments.
- The query must be executable on SAP HANA directly.
- If the question is ambiguous, make reasonable assumptions that produce the most useful result.
- Always SELECT meaningful columns, not just SELECT *.
- Add ORDER BY where it helps readability of results."""

    user_prompt = (
        f'User question: "{state["user_query"]}"{correction_section}\n\nGenerate the SAP HANA SQL query now:'
    )

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        sql = str(response.content).strip()
        sql = re.sub(r'^```sql\s*', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'^```\s*', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\s*```$', '', sql, flags=re.IGNORECASE).strip()

        return {
            **state,
            "generated_sql": sql,
            "iteration": iteration,
            "agent_log": state["agent_log"] + [
                log_prefix,
                f"[SQLGenerator] Generated SQL:\n{sql}",
            ],
        }

    except Exception as e:
        return {
            **state,
            "error": f"SQLGenerator failed: {e}",
            "agent_log": state["agent_log"] + [log_prefix, f"[SQLGenerator] ERROR: {e}"],
        }
