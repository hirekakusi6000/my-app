import { api } from "./client.js";

export const organizationApi = {
  get: () => api.get("/organization"),
  rename: (name) => api.patch("/organization", { name }),
  remove: (password, confirmName) =>
    api.delete("/organization", { password, confirm_name: confirmName }),
  sampleDataStatus: () => api.get("/organization/sample-data"),
  createSampleData: () => api.post("/organization/sample-data"),
};
