/**
 * AGENT 2 — SQL Generator
 *
 * Takes the curated schema context from the Schema Extractor and generates
 * a SAP HANA–compatible SQL query that answers the user's question.
 * If there is previous validation feedback, it uses that to correct the query.
 */

import { ChatOpenAI } from "@langchain/openai";
import { AgentState } from "../state.js";

function buildLLM(): ChatOpenAI {
  return new ChatOpenAI({
    model: "gpt-5.2",
    temperature: 0,
    configuration: {
      baseURL: process.env.AI_INTEGRATIONS_OPENAI_BASE_URL,
      apiKey: process.env.AI_INTEGRATIONS_OPENAI_API_KEY,
    },
  });
}

const HANA_SQL_RULES = `SAP HANA SQL dialect rules you MUST follow:
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
14. Boolean: no BOOLEAN type, use TINYINT (0/1) or IS_ACTIVE = 1`;

export async function sqlGeneratorAgent(state: AgentState): Promise<Partial<AgentState>> {
  if (state.error) return {};

  const llm = buildLLM();
  const iteration = state.iteration + 1;

  const correctionSection =
    state.iteration > 0 && state.validationFeedback
      ? `\n\nPREVIOUS ATTEMPT FAILED — Validator feedback to fix:\n${state.validationFeedback}\n\nPrevious SQL:\n${state.generatedSQL}\n\nPlease fix ALL the issues mentioned above.`
      : "";

  const systemPrompt = `You are an expert SAP HANA SQL developer.
Generate a correct, efficient SQL query for SAP HANA that answers the user's question.

${HANA_SQL_RULES}

Available schema:
${state.schemaContext}

Rules for your response:
- Output ONLY the SQL query, no explanations, no markdown code fences, no comments.
- The query must be executable on SAP HANA directly.
- If the question is ambiguous, make reasonable assumptions that produce the most useful result.
- Always SELECT meaningful columns, not just SELECT *.
- Add ORDER BY where it helps readability of results.`;

  const userPrompt = `User question: "${state.userQuery}"${correctionSection}

Generate the SAP HANA SQL query now:`;

  const log = `[SQLGenerator] Iteration ${iteration} — generating SQL`;

  try {
    const response = await llm.invoke([
      { role: "system", content: systemPrompt },
      { role: "user", content: userPrompt },
    ]);

    let sql = String(response.content).trim();
    sql = sql.replace(/^```sql\s*/i, "").replace(/^```\s*/i, "").replace(/\s*```$/i, "").trim();

    return {
      generatedSQL: sql,
      iteration,
      agentLog: [
        ...state.agentLog,
        log,
        `[SQLGenerator] Generated SQL:\n${sql}`,
      ],
    };
  } catch (err) {
    const errMsg = err instanceof Error ? err.message : String(err);
    return {
      error: `SQLGenerator failed: ${errMsg}`,
      agentLog: [...state.agentLog, log, `[SQLGenerator] ERROR: ${errMsg}`],
    };
  }
}
