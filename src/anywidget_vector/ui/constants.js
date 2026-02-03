// UI constants shared across components

export const BACKENDS = {
  qdrant: {
    name: "Qdrant",
    side: "browser",
    hasAuth: true,
    hasCollection: true,
    queryLanguage: "json",
    placeholder: '{"vector": [...], "limit": 10}',
  },
  pinecone: {
    name: "Pinecone",
    side: "browser",
    hasAuth: true,
    hasIndex: true,
    queryLanguage: "json",
    placeholder: '{"vector": [...], "topK": 10}',
  },
  weaviate: {
    name: "Weaviate",
    side: "browser",
    hasAuth: true,
    hasClass: true,
    queryLanguage: "graphql",
    placeholder: '{ Get { Class(limit: 10) { ... } } }',
  },
  chroma: {
    name: "Chroma",
    side: "python",
    hasCollection: true,
    queryLanguage: "dict",
    placeholder: '{"query_embeddings": [...], "n_results": 10}',
  },
  lancedb: {
    name: "LanceDB",
    side: "python",
    hasTable: true,
    queryLanguage: "sql",
    placeholder: 'category = "tech" AND year > 2020',
  },
  grafeo: {
    name: "Grafeo",
    side: "python",
    queryLanguage: "grafeo",
    placeholder: "MATCH (n:Vector) RETURN n LIMIT 10",
  },
};

export const COLOR_SCALES = {
  viridis: [[0.267,0.004,0.329],[0.282,0.140,0.458],[0.253,0.265,0.530],[0.206,0.371,0.553],[0.163,0.471,0.558],[0.127,0.566,0.551],[0.134,0.658,0.518],[0.267,0.749,0.441],[0.478,0.821,0.318],[0.741,0.873,0.150],[0.993,0.906,0.144]],
  plasma: [[0.050,0.030,0.528],[0.254,0.014,0.615],[0.417,0.001,0.658],[0.578,0.015,0.643],[0.716,0.135,0.538],[0.826,0.268,0.407],[0.906,0.411,0.271],[0.959,0.567,0.137],[0.981,0.733,0.106],[0.964,0.903,0.259],[0.940,0.975,0.131]],
  inferno: [[0.001,0.000,0.014],[0.046,0.031,0.186],[0.140,0.046,0.357],[0.258,0.039,0.406],[0.366,0.071,0.432],[0.478,0.107,0.429],[0.591,0.148,0.404],[0.706,0.206,0.347],[0.815,0.290,0.259],[0.905,0.411,0.145],[0.969,0.565,0.026]],
  magma: [[0.001,0.000,0.014],[0.035,0.028,0.144],[0.114,0.049,0.315],[0.206,0.053,0.431],[0.306,0.064,0.505],[0.413,0.086,0.531],[0.529,0.113,0.527],[0.654,0.158,0.501],[0.776,0.232,0.459],[0.878,0.338,0.418],[0.953,0.468,0.392]],
  cividis: [[0.000,0.135,0.304],[0.000,0.179,0.345],[0.117,0.222,0.360],[0.214,0.263,0.365],[0.293,0.304,0.370],[0.366,0.345,0.375],[0.437,0.387,0.382],[0.509,0.429,0.393],[0.582,0.473,0.409],[0.659,0.520,0.431],[0.739,0.570,0.461]],
  turbo: [[0.190,0.072,0.232],[0.254,0.265,0.530],[0.163,0.471,0.558],[0.134,0.658,0.518],[0.478,0.821,0.318],[0.741,0.873,0.150],[0.993,0.906,0.144],[0.988,0.652,0.198],[0.925,0.394,0.235],[0.796,0.177,0.214],[0.480,0.016,0.110]],
};

export const CATEGORICAL_COLORS = [
  "#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6",
  "#06b6d4", "#f97316", "#84cc16", "#ec4899", "#14b8a6"
];

export const SHAPES = ["sphere", "cube", "cone", "tetrahedron", "octahedron", "cylinder"];
