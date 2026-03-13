/**
 * TABLE REGISTRY — plug-and-play configuration for all HANA DB tables.
 *
 * To add a new table:
 *   1. Create a new TableDefinition object below.
 *   2. Add it to the `tableRegistry` array.
 *   3. That's it — all agents will automatically be aware of the new table.
 */

export interface ColumnDefinition {
  name: string;
  type: string;
  description: string;
  nullable?: boolean;
  primaryKey?: boolean;
}

export interface TableDefinition {
  schema: string;
  tableName: string;
  fullName: string;
  description: string;
  columns: ColumnDefinition[];
  sampleJoins?: string[];
}

const tableRegistry: TableDefinition[] = [
  {
    schema: "SALES",
    tableName: "ORDERS",
    fullName: "SALES.ORDERS",
    description: "Records of all customer orders placed in the system",
    columns: [
      { name: "ORDER_ID", type: "NVARCHAR(36)", description: "Unique order identifier", primaryKey: true, nullable: false },
      { name: "CUSTOMER_ID", type: "NVARCHAR(36)", description: "Reference to the customer who placed the order", nullable: false },
      { name: "ORDER_DATE", type: "DATE", description: "Date the order was placed", nullable: false },
      { name: "STATUS", type: "NVARCHAR(20)", description: "Order status: PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED", nullable: false },
      { name: "TOTAL_AMOUNT", type: "DECIMAL(15,2)", description: "Total monetary value of the order", nullable: false },
      { name: "CURRENCY", type: "NVARCHAR(3)", description: "ISO currency code, e.g. USD, EUR", nullable: false },
      { name: "REGION", type: "NVARCHAR(50)", description: "Geographic region of the order", nullable: true },
      { name: "CREATED_AT", type: "TIMESTAMP", description: "Timestamp when the record was created", nullable: false },
    ],
    sampleJoins: ["JOIN SALES.CUSTOMERS ON SALES.ORDERS.CUSTOMER_ID = SALES.CUSTOMERS.CUSTOMER_ID"],
  },
  {
    schema: "SALES",
    tableName: "CUSTOMERS",
    fullName: "SALES.CUSTOMERS",
    description: "Master data for all customers",
    columns: [
      { name: "CUSTOMER_ID", type: "NVARCHAR(36)", description: "Unique customer identifier", primaryKey: true, nullable: false },
      { name: "CUSTOMER_NAME", type: "NVARCHAR(200)", description: "Full name or company name of the customer", nullable: false },
      { name: "EMAIL", type: "NVARCHAR(255)", description: "Primary email address", nullable: true },
      { name: "COUNTRY", type: "NVARCHAR(3)", description: "ISO 3-letter country code", nullable: true },
      { name: "SEGMENT", type: "NVARCHAR(50)", description: "Customer segment: ENTERPRISE, SMB, RETAIL", nullable: true },
      { name: "CREATED_AT", type: "TIMESTAMP", description: "Timestamp when the customer record was created", nullable: false },
    ],
    sampleJoins: [],
  },
  {
    schema: "SALES",
    tableName: "ORDER_ITEMS",
    fullName: "SALES.ORDER_ITEMS",
    description: "Individual line items within each order",
    columns: [
      { name: "ITEM_ID", type: "NVARCHAR(36)", description: "Unique line item identifier", primaryKey: true, nullable: false },
      { name: "ORDER_ID", type: "NVARCHAR(36)", description: "Reference to the parent order", nullable: false },
      { name: "PRODUCT_ID", type: "NVARCHAR(36)", description: "Reference to the product", nullable: false },
      { name: "QUANTITY", type: "INTEGER", description: "Number of units ordered", nullable: false },
      { name: "UNIT_PRICE", type: "DECIMAL(15,2)", description: "Price per unit at the time of order", nullable: false },
      { name: "DISCOUNT_PCT", type: "DECIMAL(5,2)", description: "Discount percentage applied (0-100)", nullable: true },
    ],
    sampleJoins: [
      "JOIN SALES.ORDERS ON SALES.ORDER_ITEMS.ORDER_ID = SALES.ORDERS.ORDER_ID",
      "JOIN INVENTORY.PRODUCTS ON SALES.ORDER_ITEMS.PRODUCT_ID = INVENTORY.PRODUCTS.PRODUCT_ID",
    ],
  },
  {
    schema: "INVENTORY",
    tableName: "PRODUCTS",
    fullName: "INVENTORY.PRODUCTS",
    description: "Product catalog with pricing and inventory levels",
    columns: [
      { name: "PRODUCT_ID", type: "NVARCHAR(36)", description: "Unique product identifier", primaryKey: true, nullable: false },
      { name: "PRODUCT_NAME", type: "NVARCHAR(200)", description: "Display name of the product", nullable: false },
      { name: "CATEGORY", type: "NVARCHAR(100)", description: "Product category", nullable: true },
      { name: "UNIT_COST", type: "DECIMAL(15,2)", description: "Cost to the company per unit", nullable: true },
      { name: "STOCK_QTY", type: "INTEGER", description: "Current stock quantity available", nullable: false },
      { name: "IS_ACTIVE", type: "TINYINT", description: "1 if the product is active, 0 if discontinued", nullable: false },
    ],
    sampleJoins: [],
  },
  {
    schema: "HR",
    tableName: "EMPLOYEES",
    fullName: "HR.EMPLOYEES",
    description: "Employee master data",
    columns: [
      { name: "EMPLOYEE_ID", type: "NVARCHAR(36)", description: "Unique employee identifier", primaryKey: true, nullable: false },
      { name: "FIRST_NAME", type: "NVARCHAR(100)", description: "Employee first name", nullable: false },
      { name: "LAST_NAME", type: "NVARCHAR(100)", description: "Employee last name", nullable: false },
      { name: "DEPARTMENT", type: "NVARCHAR(100)", description: "Department the employee belongs to", nullable: true },
      { name: "HIRE_DATE", type: "DATE", description: "Date the employee was hired", nullable: true },
      { name: "SALARY", type: "DECIMAL(15,2)", description: "Current annual salary", nullable: true },
      { name: "MANAGER_ID", type: "NVARCHAR(36)", description: "EMPLOYEE_ID of this employee's direct manager", nullable: true },
    ],
    sampleJoins: [
      "JOIN HR.EMPLOYEES MGR ON HR.EMPLOYEES.MANAGER_ID = MGR.EMPLOYEE_ID",
    ],
  },
];

export default tableRegistry;

export function getTableByName(fullName: string): TableDefinition | undefined {
  return tableRegistry.find(
    (t) => t.fullName.toUpperCase() === fullName.toUpperCase()
  );
}

export function getAllTableSummaries(): string {
  return tableRegistry
    .map(
      (t) =>
        `TABLE: ${t.fullName}\n  Description: ${t.description}\n  Columns: ${t.columns.map((c) => `${c.name} (${c.type})`).join(", ")}`
    )
    .join("\n\n");
}

export function getTableSchemaText(tables: TableDefinition[]): string {
  return tables
    .map((t) => {
      const cols = t.columns
        .map(
          (c) =>
            `    ${c.name} ${c.type}${c.primaryKey ? " PRIMARY KEY" : ""}${c.nullable === false ? " NOT NULL" : ""} -- ${c.description}`
        )
        .join("\n");
      const joins =
        t.sampleJoins && t.sampleJoins.length > 0
          ? `\n  -- Sample JOINs:\n  --   ${t.sampleJoins.join("\n  --   ")}`
          : "";
      return `-- ${t.description}\nCREATE TABLE ${t.fullName} (\n${cols}\n);${joins}`;
    })
    .join("\n\n");
}
