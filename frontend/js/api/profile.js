import { api } from "./client.js";

export const profileApi = {
  getMine: () => api.get("/me/profile"),
  save: ({ name, birthDate, positionName, jobTypeName, defaultSeatId = null }) =>
    api.put("/me/profile", {
      name,
      birth_date: birthDate,
      position_name: positionName || null,
      job_type_name: jobTypeName || null,
      default_seat_id: defaultSeatId,
    }),
  saveSkills: (skills) => api.put("/me/skills", { skills }),
  uploadAvatar: (file) => {
    const body = new FormData();
    body.append("file", file);
    return api.put("/me/avatar", body);
  },
  deleteAvatar: () => api.delete("/me/avatar"),
  get: (userId) => api.get(`/profiles/${userId}`),
};
