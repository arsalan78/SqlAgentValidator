import { useQuery, useMutation } from "@tanstack/react-query";

export interface ColumnInfo {
  name: string;
  type: string;
  description: string;
  primary_key: boolean;
  nullable: boolean;
}

export interface TableInfo {
  schema: string;
  table_name: string;
  full_name: string;
  description: string;
  columns: ColumnInfo[];
}

export interface TablesResponse {
  tables: TableInfo[];
}

export interface GenerateSQLRequest {
  query: string;
  max_iterations?: number;
}

export interface GenerateSQLResponse {
  query: string;
  sql: string;
  passed: boolean;
  iterations: number;
  feedback: string | null;
  agent_log: string[];
  error: string | null;
}

export function useTables() {
  return useQuery<TablesResponse>({
    queryKey: ["/api/fastapi/sql-agent/tables"],
    queryFn: async () => {
      const res = await fetch("/api/fastapi/sql-agent/tables");
      if (!res.ok) {
        throw new Error("Failed to fetch tables");
      }
      return res.json();
    },
    staleTime: 1000 * 60 * 5, // Cache for 5 mins
  });
}

export function useGenerateSql() {
  return useMutation<GenerateSQLResponse, Error, GenerateSQLRequest>({
    mutationFn: async (data) => {
      const res = await fetch("/api/fastapi/sql-agent/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: data.query,
          max_iterations: data.max_iterations || 5,
        }),
      });
      
      const responseData = await res.json();
      
      if (!res.ok) {
        throw new Error(responseData.detail || responseData.error || "Failed to generate SQL");
      }
      
      return responseData;
    },
  });
}
