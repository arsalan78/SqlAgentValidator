"""
SAP HANA Connection Manager
Uses hdbcli — the official SAP HANA Python client.

Reads credentials from environment variables:
  HANA_HOST      — HANA host (e.g. myhost.hanacloud.ondemand.com)
  HANA_PORT      — port (443 for HANA Cloud, 30015 for on-premise)
  HANA_USER      — database user
  HANA_PASSWORD  — password (stored as Replit secret)
  HANA_SCHEMA    — default schema (optional)
"""

import os
from typing import Optional
from hdbcli import dbapi


def get_connection() -> dbapi.Connection:
    host = os.environ.get("HANA_HOST", "")
    port = int(os.environ.get("HANA_PORT", "443"))
    user = os.environ.get("HANA_USER", "")
    password = os.environ.get("HANA_PASSWORD", "")
    schema = os.environ.get("HANA_SCHEMA", "")

    if not host or not user or not password:
        raise ConnectionError(
            "HANA credentials not configured. "
            "Set HANA_HOST, HANA_USER, HANA_PASSWORD (and optionally HANA_PORT, HANA_SCHEMA) "
            "as environment variables or Replit secrets."
        )

    conn = dbapi.connect(
        address=host,
        port=port,
        user=user,
        password=password,
        encrypt=True,
        sslValidateCertificate=False,
    )

    if schema:
        cursor = conn.cursor()
        cursor.execute(f'SET SCHEMA "{schema}"')
        cursor.close()

    return conn


def test_connection() -> dict:
    """Try to connect and return version info."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION FROM SYS.M_DATABASE")
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return {"connected": True, "version": row[0] if row else "unknown"}
    except Exception as e:
        return {"connected": False, "error": str(e)}


def execute_query(sql: str, max_rows: int = 100) -> dict:
    """
    Execute a SELECT query and return columns + rows.
    Returns dict with keys: columns, rows, row_count, error
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(max_rows)
        row_count = cursor.rowcount
        cursor.close()
        conn.close()
        return {
            "columns": columns,
            "rows": [list(r) for r in rows],
            "row_count": row_count,
            "error": None,
        }
    except Exception as e:
        return {"columns": [], "rows": [], "row_count": 0, "error": str(e)}


def get_schema_from_hana(schemas: Optional[list] = None) -> list:
    """
    Introspect HANA's SYS.TABLES and SYS.TABLE_COLUMNS to build
    the live table registry — no static registry needed.

    If `schemas` is provided, only those schemas are scanned.
    Falls back to the default HANA_SCHEMA env var.
    """
    default_schema = os.environ.get("HANA_SCHEMA", "")
    if not schemas:
        schemas = [default_schema] if default_schema else []

    try:
        conn = get_connection()
        cursor = conn.cursor()

        if schemas:
            schema_placeholders = ", ".join(f"'{s.upper()}'" for s in schemas)
            tables_sql = f"""
                SELECT SCHEMA_NAME, TABLE_NAME, COMMENTS
                FROM SYS.TABLES
                WHERE SCHEMA_NAME IN ({schema_placeholders})
                  AND TABLE_TYPE = 'COLUMN'
                ORDER BY SCHEMA_NAME, TABLE_NAME
            """
        else:
            tables_sql = """
                SELECT SCHEMA_NAME, TABLE_NAME, COMMENTS
                FROM SYS.TABLES
                WHERE TABLE_TYPE = 'COLUMN'
                  AND SCHEMA_NAME NOT LIKE 'SYS%'
                  AND SCHEMA_NAME NOT LIKE '_SYS%'
                ORDER BY SCHEMA_NAME, TABLE_NAME
                FETCH FIRST 50 ROWS ONLY
            """

        cursor.execute(tables_sql)
        tables = cursor.fetchall()

        result = []
        for schema_name, table_name, comments in tables:
            cols_sql = f"""
                SELECT COLUMN_NAME, DATA_TYPE_NAME, COMMENTS,
                       IS_NULLABLE, POSITION
                FROM SYS.TABLE_COLUMNS
                WHERE SCHEMA_NAME = '{schema_name}'
                  AND TABLE_NAME = '{table_name}'
                ORDER BY POSITION
            """
            cursor.execute(cols_sql)
            cols = cursor.fetchall()

            result.append({
                "schema": schema_name,
                "table_name": table_name,
                "full_name": f"{schema_name}.{table_name}",
                "description": comments or f"Table {schema_name}.{table_name}",
                "columns": [
                    {
                        "name": col[0],
                        "type": col[1],
                        "description": col[2] or "",
                        "nullable": col[3] == "TRUE",
                        "primary_key": False,
                    }
                    for col in cols
                ],
            })

        cursor.close()
        conn.close()
        return result

    except Exception as e:
        return [{"error": str(e)}]
