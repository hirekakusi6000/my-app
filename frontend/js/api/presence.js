import { api } from "./client.js";

export const presenceApi = {
  getMine: () => api.get("/me/presence"),
  /**
   * @param {"present" | "away" | "remote" | "not_working"} status
   * @param {{ seatId?: number | null, comment?: string | null }} options comment を省略するとコメントは変わらない
   */
  update(status, { seatId = null, comment } = {}) {
    const body = { status, seat_id: seatId };
    if (comment !== undefined) body.comment = comment;
    return api.put("/me/presence", body);
  },
  list: () => api.get("/presence"),
  releaseSeat: (seatId) => api.delete(`/seats/${seatId}/occupant`),
  resetStale: () => api.post("/presence/reset-stale"),
};
