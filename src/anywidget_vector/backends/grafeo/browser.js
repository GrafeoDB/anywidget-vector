/**
 * Grafeo Server browser-side client for vector queries.
 * Mirrors the qdrant/client.js pattern.
 */

/**
 * Execute a query against Grafeo server.
 */
export async function executeQuery(query, config) {
  const url = config.url || "http://localhost:7474";
  const headers = { "Content-Type": "application/json" };

  if (config.authToken) {
    headers["Authorization"] = "Bearer " + config.authToken;
  } else if (config.username && config.password) {
    headers["Authorization"] = "Basic " + btoa(config.username + ":" + config.password);
  }

  const body = { query, language: config.language || "gql" };
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
    throw new Error("Grafeo error: " + (errText || resp.status));
  }

  return await resp.json();
}

/**
 * Convert Grafeo server result to points array.
 */
export function toPoints(response) {
  const points = [];
  const columns = response.columns || [];
  const rows = response.rows || response.data || [];

  for (let i = 0; i < rows.length; i++) {
    const row = Array.isArray(rows[i]) ? rows[i] : columns.map((c) => rows[i][c]);
    const point = { id: `point_${i}` };

    for (let c = 0; c < columns.length && c < row.length; c++) {
      const col = columns[c];
      const val = row[c];

      if (col === "id" || col === "ID") {
        point.id = String(val);
      } else if (col === "vector" || col === "embedding" || col === "embeddings") {
        const vec = Array.isArray(val) ? val : [];
        point.x = vec[0] ?? 0;
        point.y = vec[1] ?? 0;
        point.z = vec[2] ?? 0;
        point.vector = vec;
      } else if (col === "x" || col === "y" || col === "z") {
        point[col] = typeof val === "number" ? val : parseFloat(val) || 0;
      } else if (val !== null && val !== undefined) {
        // Handle nested node objects
        if (typeof val === "object" && val.properties) {
          Object.assign(point, val.properties);
          if (val.id !== undefined) point.id = String(val.id);
          if (val.properties?.vector) {
            const vec = val.properties.vector;
            point.x = vec[0] ?? point.x ?? 0;
            point.y = vec[1] ?? point.y ?? 0;
            point.z = vec[2] ?? point.z ?? 0;
            point.vector = vec;
          }
        } else {
          point[col] = val;
        }
      }
    }

    // Default coordinates if not set
    point.x = point.x ?? 0;
    point.y = point.y ?? 0;
    point.z = point.z ?? 0;
    points.push(point);
  }

  return points;
}
