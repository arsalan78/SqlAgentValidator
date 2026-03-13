"""
TABLE REGISTRY — plug-and-play configuration for all HANA DB tables.

To add a new table:
  1. Create a new dict entry below following the same schema.
  2. Add it to the TABLE_REGISTRY list.
  3. Done — all agents automatically pick it up.
"""

from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class ColumnDefinition:
    name: str
    type: str
    description: str
    nullable: bool = True
    primary_key: bool = False


@dataclass
class TableDefinition:
    schema: str
    table_name: str
    full_name: str
    description: str
    columns: List[ColumnDefinition]
    sample_joins: List[str] = field(default_factory=list)


TABLE_REGISTRY: List[TableDefinition] = [
    TableDefinition(
        schema="SALES",
        table_name="ORDERS",
        full_name="SALES.ORDERS",
        description="Records of all customer orders placed in the system",
        columns=[
            ColumnDefinition("ORDER_ID", "NVARCHAR(36)", "Unique order identifier", nullable=False, primary_key=True),
            ColumnDefinition("CUSTOMER_ID", "NVARCHAR(36)", "Reference to the customer who placed the order", nullable=False),
            ColumnDefinition("ORDER_DATE", "DATE", "Date the order was placed", nullable=False),
            ColumnDefinition("STATUS", "NVARCHAR(20)", "Order status: PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED", nullable=False),
            ColumnDefinition("TOTAL_AMOUNT", "DECIMAL(15,2)", "Total monetary value of the order", nullable=False),
            ColumnDefinition("CURRENCY", "NVARCHAR(3)", "ISO currency code, e.g. USD, EUR", nullable=False),
            ColumnDefinition("REGION", "NVARCHAR(50)", "Geographic region of the order"),
            ColumnDefinition("CREATED_AT", "TIMESTAMP", "Timestamp when the record was created", nullable=False),
        ],
        sample_joins=["JOIN SALES.CUSTOMERS ON SALES.ORDERS.CUSTOMER_ID = SALES.CUSTOMERS.CUSTOMER_ID"],
    ),
    TableDefinition(
        schema="SALES",
        table_name="CUSTOMERS",
        full_name="SALES.CUSTOMERS",
        description="Master data for all customers",
        columns=[
            ColumnDefinition("CUSTOMER_ID", "NVARCHAR(36)", "Unique customer identifier", nullable=False, primary_key=True),
            ColumnDefinition("CUSTOMER_NAME", "NVARCHAR(200)", "Full name or company name", nullable=False),
            ColumnDefinition("EMAIL", "NVARCHAR(255)", "Primary email address"),
            ColumnDefinition("COUNTRY", "NVARCHAR(3)", "ISO 3-letter country code"),
            ColumnDefinition("SEGMENT", "NVARCHAR(50)", "Customer segment: ENTERPRISE, SMB, RETAIL"),
            ColumnDefinition("CREATED_AT", "TIMESTAMP", "Timestamp when the customer record was created", nullable=False),
        ],
    ),
    TableDefinition(
        schema="SALES",
        table_name="ORDER_ITEMS",
        full_name="SALES.ORDER_ITEMS",
        description="Individual line items within each order",
        columns=[
            ColumnDefinition("ITEM_ID", "NVARCHAR(36)", "Unique line item identifier", nullable=False, primary_key=True),
            ColumnDefinition("ORDER_ID", "NVARCHAR(36)", "Reference to the parent order", nullable=False),
            ColumnDefinition("PRODUCT_ID", "NVARCHAR(36)", "Reference to the product", nullable=False),
            ColumnDefinition("QUANTITY", "INTEGER", "Number of units ordered", nullable=False),
            ColumnDefinition("UNIT_PRICE", "DECIMAL(15,2)", "Price per unit at time of order", nullable=False),
            ColumnDefinition("DISCOUNT_PCT", "DECIMAL(5,2)", "Discount percentage applied (0-100)"),
        ],
        sample_joins=[
            "JOIN SALES.ORDERS ON SALES.ORDER_ITEMS.ORDER_ID = SALES.ORDERS.ORDER_ID",
            "JOIN INVENTORY.PRODUCTS ON SALES.ORDER_ITEMS.PRODUCT_ID = INVENTORY.PRODUCTS.PRODUCT_ID",
        ],
    ),
    TableDefinition(
        schema="INVENTORY",
        table_name="PRODUCTS",
        full_name="INVENTORY.PRODUCTS",
        description="Product catalog with pricing and inventory levels",
        columns=[
            ColumnDefinition("PRODUCT_ID", "NVARCHAR(36)", "Unique product identifier", nullable=False, primary_key=True),
            ColumnDefinition("PRODUCT_NAME", "NVARCHAR(200)", "Display name of the product", nullable=False),
            ColumnDefinition("CATEGORY", "NVARCHAR(100)", "Product category"),
            ColumnDefinition("UNIT_COST", "DECIMAL(15,2)", "Cost to the company per unit"),
            ColumnDefinition("STOCK_QTY", "INTEGER", "Current stock quantity available", nullable=False),
            ColumnDefinition("IS_ACTIVE", "TINYINT", "1 if product is active, 0 if discontinued", nullable=False),
        ],
    ),
    TableDefinition(
        schema="HR",
        table_name="EMPLOYEES",
        full_name="HR.EMPLOYEES",
        description="Employee master data",
        columns=[
            ColumnDefinition("EMPLOYEE_ID", "NVARCHAR(36)", "Unique employee identifier", nullable=False, primary_key=True),
            ColumnDefinition("FIRST_NAME", "NVARCHAR(100)", "Employee first name", nullable=False),
            ColumnDefinition("LAST_NAME", "NVARCHAR(100)", "Employee last name", nullable=False),
            ColumnDefinition("DEPARTMENT", "NVARCHAR(100)", "Department the employee belongs to"),
            ColumnDefinition("HIRE_DATE", "DATE", "Date the employee was hired"),
            ColumnDefinition("SALARY", "DECIMAL(15,2)", "Current annual salary"),
            ColumnDefinition("MANAGER_ID", "NVARCHAR(36)", "EMPLOYEE_ID of this employee's direct manager"),
        ],
        sample_joins=["JOIN HR.EMPLOYEES MGR ON HR.EMPLOYEES.MANAGER_ID = MGR.EMPLOYEE_ID"],
    ),
]


def get_all_table_summaries() -> str:
    lines = []
    for t in TABLE_REGISTRY:
        cols = ", ".join(f"{c.name} ({c.type})" for c in t.columns)
        lines.append(f"TABLE: {t.full_name}\n  Description: {t.description}\n  Columns: {cols}")
    return "\n\n".join(lines)


def get_table_schema_ddl(tables: List[TableDefinition]) -> str:
    parts = []
    for t in tables:
        col_lines = []
        for c in t.columns:
            pk = " PRIMARY KEY" if c.primary_key else ""
            nn = " NOT NULL" if not c.nullable else ""
            col_lines.append(f"    {c.name} {c.type}{pk}{nn}  -- {c.description}")
        ddl = f"-- {t.description}\nCREATE TABLE {t.full_name} (\n" + "\n".join(col_lines) + "\n);"
        if t.sample_joins:
            ddl += "\n-- Sample JOINs:\n" + "\n".join(f"--   {j}" for j in t.sample_joins)
        parts.append(ddl)
    return "\n\n".join(parts)


def find_tables_by_names(names: List[str]) -> List[TableDefinition]:
    upper_names = [n.upper() for n in names]
    return [t for t in TABLE_REGISTRY if t.full_name.upper() in upper_names]
