import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Simple regex-based syntax highlighter for SQL since we didn't add a heavy library
export function highlightSQL(sql: string) {
  if (!sql) return "";
  
  let highlighted = sql
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|GROUP BY|ORDER BY|HAVING|LIMIT|TOP|OFFSET|AS|AND|OR|NOT|IN|IS|NULL|CASE|WHEN|THEN|ELSE|END|CAST|SUM|COUNT|MAX|MIN|AVG|OVER|PARTITION|ASC|DESC)\b/gi, '<span class="text-cyan-400 font-semibold">$1</span>')
    .replace(/\b(NVARCHAR|VARCHAR|INTEGER|DECIMAL|DATE|TIMESTAMP|TINYINT)\b/gi, '<span class="text-emerald-300 font-semibold">$1</span>')
    .replace(/'([^']*)'/g, '<span class="text-amber-300">\'$1\'</span>')
    .replace(/\b(\d+)\b/g, '<span class="text-purple-400">$1</span>')
    .replace(/(=|<>|!=|<|>|<=|>=|\+|-|\*|\/)/g, '<span class="text-slate-400">$1</span>');
    
  return highlighted;
}
