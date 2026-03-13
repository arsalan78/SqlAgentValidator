/**
 * AGENT 3 — SQL Validator
 *
 * Reviews the generated SQL query for:
 *   - HANA dialect correctness (no LIMIT, proper schema-qualified names, etc.)
 *   - Semantic accuracy (does it actually answer the user's question?)
 *   - Column existence (are all referenced columns in the schema?)
 *   - JOIN correctness (are join conditions using valid foreign keys?)
 *
 * Returns { passed, feedback } — if not passed, feedback is fed back to
 * the SQL Generator for the next iteration.
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

export async function sqlValidatorAgent(state: AgentState): Promise<Partial<AgentState>> {
  if (state.error) return {};

  const llm = buildLLM();

  const systemPrompt = `You are a senior SAP HANA database architect and SQL reviewer.

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
${state.schemaContext}

Respond with a JSON object in this EXACT format (no extra text):
{
  "passed": true | false,
  "issues": ["issue 1", "issue 2"],
  "corrections": ["specific fix 1", "specific fix 2"],
  "summary": "One-sentence summary of the validation result"
}

If the query is correct, set "passed": true and leave "issues" and "corrections" as empty arrays.
If there are problems, set "passed": false and list every issue and its specific correction.`;

  const userPrompt = `User question: "${state.userQuery}"

SQL query to validate:
${state.generatedSQL}

Validate this query and return only the JSON object.`;

  const log = `[SQLValidator] Validating iteration ${state.iteration} SQL`;

  try {
    const response = await llm.invoke([
      { role: "system", content: systemPrompt },
      { role: "user", content: userPrompt },
    ]);

    const content = String(response.content).trim();
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      throw new Error(`Could not parse validation JSON from: ${content}`);
    }

    const result = JSON.parse(jsonMatch[0]) as {
      passed: boolean;
      issues: string[];
      corrections: string[];
      summary: string;
    };

    const passed = result.passed === true;
    const feedback =
      !passed && result.issues.length > 0
        ? `Issues found:\n${result.issues.map((i, idx) => `  ${idx + 1}. ${i}`).join("\n")}\n\nRequired corrections:\n${result.corrections.map((c, idx) => `  ${idx + 1}. ${c}`).join("\n")}`
        : "";

    const finalSQL = passed ? state.generatedSQL : "";

    return {
      validationPassed: passed,
      validationFeedback: feedback,
      finalSQL,
      agentLog: [
        ...state.agentLog,
        log,
        `[SQLValidator] Result: ${passed ? "PASSED ✓" : "FAILED ✗"} — ${result.summary}`,
        ...(feedback ? [`[SQLValidator] Feedback:\n${feedback}`] : []),
      ],
    };
  } catch (err) {
    const errMsg = err instanceof Error ? err.message : String(err);
    return {
      error: `SQLValidator failed: ${errMsg}`,
      agentLog: [...state.agentLog, log, `[SQLValidator] ERROR: ${errMsg}`],
    };
  }
}
