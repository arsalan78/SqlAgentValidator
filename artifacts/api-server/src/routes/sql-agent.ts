import { Router, type IRouter } from "express";
import { runSQLAgent } from "../sql-agent/graph.js";
import tableRegistry from "../sql-agent/table-registry.js";

const router: IRouter = Router();

router.post("/sql-agent/generate", async (req, res) => {
  const { query, maxIterations } = req.body as {
    query?: string;
    maxIterations?: number;
  };

  if (!query || typeof query !== "string" || query.trim() === "") {
    res.status(400).json({
      error: "Missing required field: query (non-empty string)",
    });
    return;
  }

  const iterations = typeof maxIterations === "number" && maxIterations > 0 && maxIterations <= 10
    ? maxIterations
    : 5;

  try {
    const result = await runSQLAgent(query.trim(), iterations);

    res.json({
      query: query.trim(),
      sql: result.sql,
      passed: result.passed,
      iterations: result.iterations,
      feedback: result.feedback || null,
      agentLog: result.log,
      error: result.error || null,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    res.status(500).json({ error: `Agent pipeline failed: ${message}` });
  }
});

router.get("/sql-agent/tables", (_req, res) => {
  res.json({
    tables: tableRegistry.map((t) => ({
      schema: t.schema,
      tableName: t.tableName,
      fullName: t.fullName,
      description: t.description,
      columns: t.columns.map((c) => ({
        name: c.name,
        type: c.type,
        description: c.description,
        primaryKey: c.primaryKey ?? false,
        nullable: c.nullable ?? true,
      })),
    })),
  });
});

export default router;
