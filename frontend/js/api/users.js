import { api } from "./client.js";

export const usersApi = {
  list: () => api.get("/users"),
  create: (email, initialPassword) =>
    api.post("/users", { email, initial_password: initialPassword }),
  updateEmail: (id, email) => api.patch(`/users/${id}`, { email }),
  resetPassword: (id, newPassword) =>
    api.post(`/users/${id}/password-reset`, { new_password: newPassword }),
  remove: (id) => api.delete(`/users/${id}`),
};
