/**
 * Grafeo Server browser-side client for vector queries.
 * Mirrors the qdrant/client.js pattern.
 *
 * grafeo-server API: POST /query with {query, language, database} returns
 * {columns: string[], rows: any[][]}; errors return {error, detail}.
 * The server sends no CORS headers unless started with --cors-origins.
 */
import { grafeoRowToPoint } from "./points.ts";
import type { BackendConfig, PointData } from "../../ui/types.ts";

/**
 * Execute a query against Grafeo server.
 */
export async function executeQuery(query: string, config: BackendConfig): Promise<any> {
  const url = config.url || "http://localhost:7474";
  const headers: Record<string, string> = { "Content-Type": "application/json" };

  if (config.authToken) {
    headers["Authorization"] = "Bearer " + config.authToken;
  } else if (config.username && config.password) {
    headers["Authorization"] = "Basic " + btoa(config.username + ":" + config.password);
  }

  const body: Record<string, unknown> = { query, language: config.language || "gql" };
  if (config.database && config.database !== "default") {
    body.database = config.database;
  }

  const resp = await fetch(url + "/query", {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const errText = await resp.text();
    let message = errText;
    try {
      const errBody = JSON.parse(errText);
      message = errBody.detail || errBody.error || errText;
    } catch (_) {
      // not JSON, keep the raw text
    }
    throw new Error("Grafeo error: " + (message || resp.status));
  }

  return await resp.json();
}

/**
 * Convert Grafeo server result to points array.
 */
export function toPoints(response: any): PointData[] {
  const columns = response?.columns || [];
  const rows = response?.rows || response?.data || [];

  return rows.map((row: any, i: number) => {
    const values = Array.isArray(row) ? row : columns.map((c: string) => row?.[c]);
    return grafeoRowToPoint(
      columns.map((col: string, c: number) => [col, values[c]] as [string, unknown]),
      i,
    );
  });
}
