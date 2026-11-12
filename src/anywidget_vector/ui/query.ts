// Browser-side query execution: which backend runs the query, and dropping results of superseded queries.
// Kept free of Three.js so tests can import it in Node.

import type { BackendConfig, PointData, WidgetModel } from "./types.ts";

import { executeQuery as qdrantExecute, toPoints as qdrantToPoints } from "../backends/qdrant/client.ts";
import { executeQuery as pineconeExecute, toPoints as pineconeToPoints } from "../backends/pinecone/client.ts";
import { executeQuery as weaviateExecute, toPoints as weaviateToPoints } from "../backends/weaviate/client.ts";
import * as grafeoServer from "../backends/grafeo/browser.ts";
import * as grafeoEmbed from "../backends/grafeo/embed.ts";

// The newest browser-side query per model; results of older ones are dropped
const latestQuery = new WeakMap<WidgetModel, number>();

export function startQuery(model: WidgetModel): number {
  const ticket = (latestQuery.get(model) ?? 0) + 1;
  latestQuery.set(model, ticket);
  return ticket;
}

export function isLatestQuery(model: WidgetModel, ticket: number): boolean {
  return latestQuery.get(model) === ticket;
}

// Unified query executor
export async function executeBackendQuery(model: WidgetModel): Promise<PointData[]> {
  const backend = model.get("backend");
  const query = model.get("query_input");
  const config = (model.get("backend_config") ?? {}) as BackendConfig;
  const mode = model.get("grafeo_connection_mode") || "embedded";

  let response: any, points: PointData[];

  if (backend === "grafeo" && mode === "server") {
    const serverUrl = model.get("grafeo_server_url") || "http://localhost:7474";
    const serverConfig = { ...config, url: serverUrl, language: "gql" };
    response = await grafeoServer.executeQuery(query, serverConfig);
    points = grafeoServer.toPoints(response);
  } else if (backend === "grafeo" && mode === "wasm") {
    if (!grafeoEmbed.isConnected()) {
      await grafeoEmbed.connect();
    }
    response = await grafeoEmbed.executeQuery(query, config);
    points = grafeoEmbed.toPoints(response);
  } else if (backend === "qdrant") {
    response = await qdrantExecute(query, config);
    points = qdrantToPoints(response);
  } else if (backend === "pinecone") {
    response = await pineconeExecute(query, config);
    points = pineconeToPoints(response);
  } else if (backend === "weaviate") {
    const className = config.className || config.class || "Vector";
    response = await weaviateExecute(query, config);
    points = weaviateToPoints(response, className);
  } else {
    throw new Error(`Browser backend not supported: ${backend}`);
  }

  return points;
}
