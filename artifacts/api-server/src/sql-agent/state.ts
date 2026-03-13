import { TableDefinition } from "./table-registry.js";

export interface AgentState {
  userQuery: string;
  iteration: number;
  maxIterations: number;
  relevantTables: TableDefinition[];
  schemaContext: string;
  generatedSQL: string;
  validationPassed: boolean;
  validationFeedback: string;
  finalSQL: string;
  error: string;
  agentLog: string[];
}

export const initialState = (
  userQuery: string,
  maxIterations = 5
): AgentState => ({
  userQuery,
  iteration: 0,
  maxIterations,
  relevantTables: [],
  schemaContext: "",
  generatedSQL: "",
  validationPassed: false,
  validationFeedback: "",
  finalSQL: "",
  error: "",
  agentLog: [],
});
