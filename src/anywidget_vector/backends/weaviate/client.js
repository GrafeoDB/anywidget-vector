// Weaviate browser-side client

export async function executeQuery(query, config) {
  const { url, apiKey } = config;
  const headers = { "Content-Type": "application/json" };
  if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;

  // Query is GraphQL string
  const graphql = typeof query === "string" ? query : JSON.stringify(query);

  const resp = await fetch(`${url}/v1/graphql`, {
    method: "POST",
    headers,
    body: JSON.stringify({ query: graphql }),
  });

  if (!resp.ok) throw new Error(`Weaviate error: ${await resp.text()}`);
  const data = await resp.json();

  if (data.errors) {
    throw new Error(`GraphQL error: ${data.errors[0].message}`);
  }

  return data;
}

export function toPoints(response, className) {
  const data = response?.data?.Get?.[className] || [];

  return data.map((item, i) => {
    const additional = item._additional || {};
    const vector = additional.vector || [];

    const point = {
      id: additional.id || `point_${i}`,
      score: additional.distance ? 1 - additional.distance : undefined,
      x: vector[0] ?? item.x ?? 0,
      y: vector[1] ?? item.y ?? 0,
      z: vector[2] ?? item.z ?? 0,
      vector: vector.length ? vector : undefined,
    };

    // Add other fields
    for (const [k, v] of Object.entries(item)) {
      if (k !== "_additional") point[k] = v;
    }

    return point;
  });
}
