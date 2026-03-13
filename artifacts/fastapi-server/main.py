"""
FastAPI server for the SAP HANA SQL Agent.

Routes (served at port 8000, proxied via Express at /api/fastapi/*):
  GET  /healthz                   — Health check
  POST /sql-agent/generate        — Run the 3-agent LangGraph pipeline
  GET  /sql-agent/tables          — List all registered HANA tables
  GET  /docs                      — Swagger UI
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List

from table_registry import TABLE_REGISTRY
from graph import run_sql_agent


app = FastAPI(
    title="HANA SQL Agent API",
    description="Multi-agent LangGraph pipeline for generating validated SAP HANA SQL from natural language",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    query: str = Field(..., description="Natural language question to convert to SQL", min_length=1)
    max_iterations: int = Field(5, ge=1, le=10, description="Max generate→validate loops (default 5)")


class GenerateResponse(BaseModel):
    query: str
    sql: str
    passed: bool
    iterations: int
    feedback: Optional[str] = None
    agent_log: List[str]
    error: Optional[str] = None


class ColumnInfo(BaseModel):
    name: str
    type: str
    description: str
    primary_key: bool
    nullable: bool


class TableInfo(BaseModel):
    schema_name: str = Field(..., alias="schema")
    table_name: str
    full_name: str
    description: str
    columns: List[ColumnInfo]

    class Config:
        populate_by_name = True


class TablesResponse(BaseModel):
    tables: List[TableInfo]


@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "fastapi-sql-agent"}


@app.post("/sql-agent/generate", response_model=GenerateResponse)
async def generate_sql(body: GenerateRequest):
    """
    Run the 3-agent LangGraph pipeline:
    1. Schema Extractor — identifies relevant tables from the registry
    2. SQL Generator — writes SAP HANA-compatible SQL
    3. SQL Validator — validates and loops until correct or max iterations reached
    """
    try:
        result = await run_sql_agent(body.query.strip(), body.max_iterations)
        return GenerateResponse(
            query=body.query.strip(),
            sql=result["sql"],
            passed=result["passed"],
            iterations=result["iterations"],
            feedback=result["feedback"],
            agent_log=result["log"],
            error=result["error"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent pipeline failed: {e}")


@app.get("/sql-agent/tables", response_model=TablesResponse)
def list_tables():
    """List all tables registered in the table registry."""
    return TablesResponse(
        tables=[
            TableInfo(
                **{
                    "schema": t.schema,
                    "table_name": t.table_name,
                    "full_name": t.full_name,
                    "description": t.description,
                    "columns": [
                        ColumnInfo(
                            name=c.name,
                            type=c.type,
                            description=c.description,
                            primary_key=c.primary_key,
                            nullable=c.nullable,
                        )
                        for c in t.columns
                    ],
                }
            )
            for t in TABLE_REGISTRY
        ]
    )
