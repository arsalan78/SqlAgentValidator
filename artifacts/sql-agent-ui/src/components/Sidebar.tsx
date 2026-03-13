import React, { useState } from "react";
import { Database, Table, Key, ChevronDown, ChevronRight, Loader2, Info } from "lucide-react";
import { useTables, TableInfo } from "@/hooks/use-sql-agent";
import { cn } from "@/lib/utils";
import { Badge } from "./ui";

function TableItem({ table }: { table: TableInfo }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="border-b border-border/50 last:border-0">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 hover:bg-accent/50 transition-colors text-left"
      >
        <div className="flex items-center gap-2 overflow-hidden">
          <Table className="w-4 h-4 text-primary shrink-0" />
          <span className="text-sm font-semibold truncate" title={table.full_name}>
            {table.full_name}
          </span>
        </div>
        {isOpen ? <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" /> : <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />}
      </button>

      {isOpen && (
        <div className="px-3 pb-3 bg-black/20">
          <div className="flex items-start gap-2 mb-3 text-xs text-muted-foreground bg-secondary/50 p-2 rounded-md">
            <Info className="w-3 h-3 mt-0.5 shrink-0" />
            <p>{table.description}</p>
          </div>
          
          <div className="space-y-1">
            <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-2 px-1">Columns</div>
            {table.columns.map((col, idx) => (
              <div key={idx} className="flex items-center justify-between py-1 px-1 rounded hover:bg-accent/30 group">
                <div className="flex items-center gap-1.5 overflow-hidden">
                  {col.primary_key ? (
                    <Key className="w-3 h-3 text-warning shrink-0" />
                  ) : (
                    <div className="w-3 h-3 shrink-0" /> // Spacer
                  )}
                  <span className={cn("text-xs truncate", col.primary_key ? "font-semibold text-foreground" : "text-muted-foreground")}>
                    {col.name}
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[10px] font-mono text-primary/70">{col.type}</span>
                  {!col.nullable && <span className="text-[9px] bg-secondary px-1 rounded text-secondary-foreground">NN</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function Sidebar() {
  const { data, isLoading, error } = useTables();

  return (
    <div className="w-full md:w-80 border-l border-border bg-card/80 backdrop-blur-xl flex flex-col h-full z-10">
      <div className="p-4 border-b border-border flex items-center gap-3 bg-background/50">
        <div className="p-2 bg-primary/10 rounded-lg">
          <Database className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h2 className="font-semibold text-sm">HANA Database</h2>
          <p className="text-xs text-muted-foreground">Plug-and-play Schema Registry</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-40 text-muted-foreground">
            <Loader2 className="w-6 h-6 animate-spin mb-2" />
            <span className="text-xs">Loading schema...</span>
          </div>
        ) : error ? (
          <div className="p-4 text-sm text-destructive bg-destructive/10 m-4 rounded-md">
            Failed to load tables. Ensure the backend is running.
          </div>
        ) : data?.tables?.length === 0 ? (
          <div className="p-4 text-sm text-muted-foreground text-center mt-10">
            No tables registered in table_registry.py
          </div>
        ) : (
          <div className="flex flex-col">
            <div className="px-4 py-2 bg-secondary/30 flex items-center justify-between border-b border-border/50">
              <span className="text-xs font-medium text-muted-foreground">Available Tables</span>
              <Badge variant="outline" className="text-[10px]">{data?.tables.length}</Badge>
            </div>
            {data?.tables.map((table, i) => (
              <TableItem key={i} table={table} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
