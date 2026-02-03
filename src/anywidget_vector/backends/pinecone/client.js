// Pinecone browser-side client

export async function executeQuery(query, config) {
  const { url, apiKey, namespace } = config;
  const headers = { "Content-Type": "application/json", "Api-Key": apiKey };

  const parsed = typeof query === "string" ? JSON.parse(query) : query;

  if (parsed.ids) {
    // Fetch by IDs
    const resp = await fetch(`${url}/vectors/fetch?${parsed.ids.map(id => `ids=${id}`).join("&")}`, {
      method: "GET",
      headers,
    });
    if (!resp.ok) throw new Error(`Pinecone error: ${await resp.text()}`);
    return await resp.json();
  }

  // Query
  const body = {
    vector: parsed.vector,
    topK: parsed.topK || parsed.limit || 10,
    includeMetadata: true,
    includeValues: true,
    filter: parsed.filter,
    namespace: parsed.namespace || namespace,
  };

  const resp = await fetch(`${url}/query`, { method: "POST", headers, body: JSON.stringify(body) });
  if (!resp.ok) throw new Error(`Pinecone error: ${await resp.text()}`);
  return await resp.json();
}

export function toPoints(response) {
  const matches = response.matches || [];
  return matches.map(m => ({
    id: m.id,
    score: m.score,
    x: m.values?.[0] ?? m.metadata?.x ?? 0,
    y: m.values?.[1] ?? m.metadata?.y ?? 0,
    z: m.values?.[2] ?? m.metadata?.z ?? 0,
    vector: m.values,
    ...m.metadata,
  }));
}
