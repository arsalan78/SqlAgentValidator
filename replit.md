# Workspace

## Overview

pnpm workspace monorepo using TypeScript. Each package manages its own dependencies.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)
- **AI/LLM**: OpenAI via Replit AI Integrations (no API key needed)
- **Agent framework**: LangGraph (`@langchain/langgraph`)

## Structure

```text
artifacts-monorepo/
├── artifacts/              # Deployable applications
│   └── api-server/         # Express API server
│       └── src/
│           ├── sql-agent/  # LangGraph SQL agent pipeline
│           │   ├── table-registry.ts   # Plug-and-play table config
│           │   ├── state.ts            # Agent shared state
│           │   ├── graph.ts            # LangGraph graph definition
│           │   └── agents/
│           │       ├── schema-extractor.ts  # Agent 1: identifies tables
│           │       ├── sql-generator.ts     # Agent 2: generates HANA SQL
│           │       └── sql-validator.ts     # Agent 3: validates & loops
│           └── routes/
│               └── sql-agent.ts  # REST API routes for the agent pipeline
├── lib/                    # Shared libraries
│   ├── api-spec/           # OpenAPI spec + Orval codegen config
│   ├── api-client-react/   # Generated React Query hooks
│   ├── api-zod/            # Generated Zod schemas from OpenAPI
│   ├── db/                 # Drizzle ORM schema + DB connection
│   ├── integrations-openai-ai-server/  # OpenAI server-side helpers
│   └── integrations-openai-ai-react/   # OpenAI React hooks
├── scripts/                # Utility scripts
├── pnpm-workspace.yaml     # pnpm workspace
├── tsconfig.base.json      # Shared TS options
├── tsconfig.json           # Root TS project references
└── package.json            # Root package
```

## SQL Agent System (SAP HANA)

### Architecture

A 3-agent LangGraph pipeline that turns natural language into validated SAP HANA SQL:

```
User Query
    │
    ▼
[Agent 1: Schema Extractor]
    Reads all tables from table-registry.ts
    Uses LLM to identify which tables/columns are needed
    │
    ▼
[Agent 2: SQL Generator]
    Uses curated schema + HANA dialect rules
    Generates HANA-compatible SQL
    If previous validation failed, uses feedback to fix query
    │
    ▼
[Agent 3: SQL Validator]
    Checks dialect correctness, semantic accuracy, column existence
    If PASSED → done
    If FAILED → sends feedback back to Agent 2 (loops up to maxIterations)
```

### Adding New Tables (Plug-and-Play)

Edit `artifacts/api-server/src/sql-agent/table-registry.ts`:

```typescript
{
  schema: "MY_SCHEMA",
  tableName: "MY_TABLE",
  fullName: "MY_SCHEMA.MY_TABLE",
  description: "What this table stores",
  columns: [
    { name: "ID", type: "NVARCHAR(36)", description: "...", primaryKey: true, nullable: false },
    { name: "NAME", type: "NVARCHAR(200)", description: "...", nullable: false },
  ],
  sampleJoins: ["JOIN OTHER.TABLE ON MY_SCHEMA.MY_TABLE.FK = OTHER.TABLE.PK"],
}
```

Add it to the `tableRegistry` array — all agents pick it up automatically.

### API Endpoints

- `POST /api/sql-agent/generate` — Generate HANA SQL from a natural language query
  - Body: `{ "query": "...", "maxIterations": 5 }`
  - Response: `{ sql, passed, iterations, feedback, agentLog, error }`
- `GET /api/sql-agent/tables` — List all registered tables with their column definitions

### Environment Variables

- `AI_INTEGRATIONS_OPENAI_BASE_URL` — Auto-provisioned by Replit AI Integrations
- `AI_INTEGRATIONS_OPENAI_API_KEY` — Auto-provisioned by Replit AI Integrations

## Packages

### `artifacts/api-server` (`@workspace/api-server`)

Express 5 API server. Routes live in `src/routes/` and use `@workspace/api-zod` for request/response validation.

- Entry: `src/index.ts` — reads `PORT`, starts Express
- App setup: `src/app.ts` — mounts CORS, JSON/urlencoded parsing, routes at `/api`
- Routes: `src/routes/index.ts` mounts sub-routers
- `pnpm --filter @workspace/api-server run dev` — run the dev server

### `lib/db` (`@workspace/db`)

Database layer using Drizzle ORM with PostgreSQL.

### `lib/api-spec` (`@workspace/api-spec`)

OpenAPI 3.1 spec + Orval config. Run codegen: `pnpm --filter @workspace/api-spec run codegen`

### `lib/api-zod` (`@workspace/api-zod`)

Generated Zod schemas from the OpenAPI spec.

### `lib/api-client-react` (`@workspace/api-client-react`)

Generated React Query hooks and fetch client from the OpenAPI spec.

### `scripts` (`@workspace/scripts`)

Utility scripts package. Each script is a `.ts` file in `src/`.
