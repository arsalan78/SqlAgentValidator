"""
AGENT 3 — SQL Validator
Validates the generated SQL for HANA dialect, semantic accuracy, and column existence.
Sends feedback back to the generator if validation fails.
"""

import json
import os
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from state import AgentState


def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-5.2",
        temperature=0,
        base_url=os.environ["AI_INTEGRATIONS_OPENAI_BASE_URL"],
        api_key=os.environ["AI_INTEGRATIONS_OPENAI_API_KEY"],
    )


def sql_validator_agent(state: AgentState) -> AgentState:
    if state["error"]:
        return state

    llm = build_llm()
    log_prefix = f"[SQLValidator] Validating iteration {state['iteration']} SQL"

    system_prompt = f"""You are a senior SAP HANA database architect and SQL reviewer.

Your job is to validate a generated SQL query against:
1. SAP HANA SQL dialect rules
2. Semantic correctness (does it answer the user's intent?)
3. Schema accuracy (do all columns and tables actually exist in the provided schema?)
4. Performance best practices

SAP HANA dialect rules:
- Use TOP N not LIMIT N
- Always use SCHEMA.TABLE_NAME fully qualified
- Use NVARCHAR not VARCHAR
- No trailing semicolons required
- Use COALESCE or IFNULL, not ISNULL
- DATE literals: DATE '2024-01-01'
- No BOOLEAN type, use TINYINT (0/1)

Available schema:
{state["schema_context"]}

Respond with a JSON object in this EXACT format (no extra text):
{{
  "passed": true | false,
  "issues": ["issue 1", "issue 2"],
  "corrections": ["specific fix 1", "specific fix 2"],
  "summary": "One-sentence summary of the validation result"
}}

If the query is correct, set "passed": true and leave "issues" and "corrections" as empty arrays.
If there are problems, set "passed": false and list every issue and its specific correction."""

    user_prompt = (
        f'User question: "{state["user_query"]}"\n\n'
        f"SQL query to validate:\n{state['generated_sql']}\n\n"
        f"Validate this query and return only the JSON object."
    )

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        content = str(response.content).strip()
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if not match:
            raise ValueError(f"Could not parse validation JSON from: {content}")

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

        new_log = state["agent_log"] + [
            log_prefix,
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
            "agent_log": state["agent_log"] + [log_prefix, f"[SQLValidator] ERROR: {e}"],
        }
