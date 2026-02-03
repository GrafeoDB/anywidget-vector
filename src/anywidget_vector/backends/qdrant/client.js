// Qdrant browser-side client

export async function executeQuery(query, config) {
  const { url, apiKey, collection } = config;
  const headers = { "Content-Type": "application/json" };
  if (apiKey) headers["api-key"] = apiKey;

  const parsed = typeof query === "string" ? JSON.parse(query) : query;
  let endpoint, body;

  if (parsed.ids) {
    endpoint = `${url}/collections/${collection}/points`;
    body = { ids: parsed.ids, with_payload: true, with_vectors: true };
  } else if (parsed.recommend) {
    endpoint = `${url}/collections/${collection}/points/recommend`;
    body = {
      positive: parsed.recommend.positive || [],
      negative: parsed.recommend.negative || [],
      limit: parsed.limit || 10,
      with_payload: true,
      with_vectors: true,
    };
  } else if (parsed.vector) {
    endpoint = `${url}/collections/${collection}/points/search`;
    body = {
      vector: parsed.vector,
      filter: parsed.filter,
      limit: parsed.limit || 10,
      with_payload: true,
      with_vectors: true,
      score_threshold: parsed.score_threshold,
    };
  } else if (parsed.filter) {
    endpoint = `${url}/collections/${collection}/points/scroll`;
    body = {
      filter: parsed.filter,
      limit: parsed.limit || 100,
      with_payload: true,
      with_vectors: true,
    };
  } else {
    throw new Error("Invalid query: need vector, ids, recommend, or filter");
  }

  const resp = await fetch(endpoint, { method: "POST", headers, body: JSON.stringify(body) });
  if (!resp.ok) throw new Error(`Qdrant error: ${await resp.text()}`);
  return await resp.json();
}

export function toPoints(response) {
  const results = response.result || response.points || [];
  return results.map(r => ({
    id: String(r.id),
    score: r.score,
    x: r.vector?.[0] ?? r.payload?.x ?? 0,
    y: r.vector?.[1] ?? r.payload?.y ?? 0,
    z: r.vector?.[2] ?? r.payload?.z ?? 0,
    vector: r.vector,
    ...r.payload,
  }));
}
