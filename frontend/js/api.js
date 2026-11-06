const API_BASE = "/api/v1";

async function request(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

export function fetchHello() {
  return request("/hello");
}
