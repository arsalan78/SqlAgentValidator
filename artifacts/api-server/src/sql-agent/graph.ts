/**
 * SQL AGENT GRAPH — LangGraph orchestration
 *
 * Flow:
 *   extract_schema → generate_sql → validate_sql
 *                                        │
 *                          ┌─────────────┴─────────────┐
 *                          │ passed                    │ failed (& iterations < max)
 *                          ▼                           ▼
 *                        END                    generate_sql (loop)
 *
 * When max iterations are reached without passing, the last generated SQL
 * is returned as the best effort along with the validation feedback.
 */

import { StateGraph, END } from "@langchain/langgraph";
import { AgentState, initialState } from "./state.js";
import { schemaExtractorAgent } from "./agents/schema-extractor.js";
import { sqlGeneratorAgent } from "./agents/sql-generator.js";
import { sqlValidatorAgent } from "./agents/sql-validator.js";

function shouldLoop(state: AgentState): "generate_sql" | typeof END {
  if (state.error) return END;
  if (state.validationPassed) return END;
  if (state.iteration >= state.maxIterations) {
    return END;
  }
  return "generate_sql";
}

export function buildSQLAgentGraph() {
  const graph = new StateGraph<AgentState>({
    channels: {
      userQuery: { value: (_a: string, b: string) => b, default: () => "" },
      iteration: { value: (_a: number, b: number) => b, default: () => 0 },
      maxIterations: { value: (_a: number, b: number) => b, default: () => 5 },
      relevantTables: { value: (_a: unknown, b: unknown) => b, default: () => [] },
      schemaContext: { value: (_a: string, b: string) => b, default: () => "" },
      generatedSQL: { value: (_a: string, b: string) => b, default: () => "" },
      validationPassed: { value: (_a: boolean, b: boolean) => b, default: () => false },
      validationFeedback: { value: (_a: string, b: string) => b, default: () => "" },
      finalSQL: { value: (_a: string, b: string) => b, default: () => "" },
      error: { value: (_a: string, b: string) => b, default: () => "" },
      agentLog: {
        value: (_a: string[], b: string[]) => b,
        default: () => [],
      },
    },
  });

  graph.addNode("extract_schema", schemaExtractorAgent);
  graph.addNode("generate_sql", sqlGeneratorAgent);
  graph.addNode("validate_sql", sqlValidatorAgent);

  graph.setEntryPoint("extract_schema");
  graph.addEdge("extract_schema", "generate_sql");
  graph.addEdge("generate_sql", "validate_sql");
  graph.addConditionalEdges("validate_sql", shouldLoop, {
    generate_sql: "generate_sql",
    [END]: END,
  });

  return graph.compile();
}

export async function runSQLAgent(
  userQuery: string,
  maxIterations = 5
): Promise<{
  sql: string;
  passed: boolean;
  iterations: number;
  feedback: string;
  log: string[];
  error: string;
}> {
  const app = buildSQLAgentGraph();
  const startState = initialState(userQuery, maxIterations);

  const result = await app.invoke(startState);

  const finalState = result as AgentState;

  return {
    sql: finalState.validationPassed
      ? finalState.finalSQL
      : finalState.generatedSQL,
    passed: finalState.validationPassed,
    iterations: finalState.iteration,
    feedback: finalState.validationFeedback,
    log: finalState.agentLog,
    error: finalState.error,
  };
}
