// API 呼び出しの共通処理。画面のコードから fetch を直接呼ばず、必ずここを通す。

const API_BASE = "/api/v1";

export class ApiError extends Error {
  constructor(status, code, message, errors = []) {
    super(message);
    this.status = status;
    this.code = code;
    this.errors = errors;
  }
}

async function request(method, path, body) {
  const options = {
    method,
    credentials: "same-origin",
    headers: {},
  };
  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const res = await fetch(`${API_BASE}${path}`, options);
  if (res.status === 204) return null;

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new ApiError(
      res.status,
      data?.code ?? "HTTP_ERROR",
      data?.detail ?? `通信エラー (${res.status})`,
      data?.errors ?? [],
    );
  }
  return data;
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body),
  put: (path, body) => request("PUT", path, body),
  patch: (path, body) => request("PATCH", path, body),
  delete: (path) => request("DELETE", path),
};
