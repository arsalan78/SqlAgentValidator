/**
 * AGENT 1 — Schema Extractor
 *
 * Reads the user's natural-language query and identifies which tables and
 * columns are relevant. Returns a curated subset of the table registry so
 * the SQL Generator only sees what it needs.
 */

import { ChatOpenAI } from "@langchain/openai";
import tableRegistry, { getAllTableSummaries, TableDefinition } from "../table-registry.js";
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

export async function schemaExtractorAgent(state: AgentState): Promise<Partial<AgentState>> {
  const llm = buildLLM();
  const allSummaries = getAllTableSummaries();

  const systemPrompt = `You are a SAP HANA database schema expert.
Given a user question, identify the EXACT table names (in SCHEMA.TABLE format) needed to answer the question.

Available tables:
${allSummaries}

Rules:
- Only list tables that are DIRECTLY needed to answer the question.
- If multiple tables are needed for a JOIN, include all of them.
- Respond with ONLY a JSON array of full table names, e.g.: ["SALES.ORDERS", "SALES.CUSTOMERS"]
- Do NOT include explanations, just the JSON array.`;

  const userPrompt = `User question: "${state.userQuery}"

Which tables are needed? Return only a JSON array of full table names.`;

  let relevantTables: TableDefinition[] = [];
  let schemaContext = "";
  const log = `[SchemaExtractor] Analyzing query: "${state.userQuery}"`;

  try {
    const response = await llm.invoke([
      { role: "system", content: systemPrompt },
      { role: "user", content: userPrompt },
    ]);

    const content = String(response.content).trim();

    const jsonMatch = content.match(/\[[\s\S]*\]/);
    if (!jsonMatch) {
      throw new Error(`Could not parse table list from LLM response: ${content}`);
    }

    const tableNames: string[] = JSON.parse(jsonMatch[0]);
    relevantTables = tableRegistry.filter((t) =>
      tableNames.some((n) => n.toUpperCase() === t.fullName.toUpperCase())
    );

    if (relevantTables.length === 0) {
      relevantTables = tableRegistry;
    }

    const { getTableSchemaText } = await import("../table-registry.js");
    schemaContext = getTableSchemaText(relevantTables);

    return {
      relevantTables,
      schemaContext,
      agentLog: [
        ...state.agentLog,
        log,
        `[SchemaExtractor] Identified tables: ${relevantTables.map((t) => t.fullName).join(", ")}`,
      ],
    };
  } catch (err) {
    const errMsg = err instanceof Error ? err.message : String(err);
    return {
      error: `SchemaExtractor failed: ${errMsg}`,
      agentLog: [...state.agentLog, log, `[SchemaExtractor] ERROR: ${errMsg}`],
    };
  }
}
