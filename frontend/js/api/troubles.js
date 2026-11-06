import { api } from "./client.js";

export const troublesApi = {
  /** @param {{ status?: "open" | "resolved", userId?: number }} filter */
  list({ status, userId } = {}) {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (userId) params.set("user_id", String(userId));
    const query = params.toString();
    return api.get(`/troubles${query ? `?${query}` : ""}`);
  },
  create: (title, body) => api.post("/troubles", { title, body }),
  update: (id, fields) => api.patch(`/troubles/${id}`, fields),
  remove: (id) => api.delete(`/troubles/${id}`),
};
