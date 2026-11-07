import { api } from "./client.js";

export const peopleApi = {
  /**
   * @param {{ name?: string, skills?: string[], minYears?: number, statuses?: string[] }} query
   */
  search({ name = "", skills = [], minYears = 0, statuses = [] } = {}) {
    const params = new URLSearchParams();
    if (name.trim()) params.set("q", name.trim());
    for (const s of skills) params.append("skill", s);
    if (minYears > 0) params.set("min_years", String(minYears));
    for (const s of statuses) params.append("status", s);
    const query = params.toString();
    return api.get(`/people${query ? `?${query}` : ""}`);
  },
};
