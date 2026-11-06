import { api } from "./client.js";

export const authApi = {
  signup: (organizationName, email, password) =>
    api.post("/auth/signup", { organization_name: organizationName, email, password }),
  login: (email, password) => api.post("/auth/login", { email, password }),
  logout: () => api.post("/auth/logout"),
  me: () => api.get("/me"),
  changePassword: (currentPassword, newPassword) =>
    api.put("/me/password", { current_password: currentPassword, new_password: newPassword }),
};
