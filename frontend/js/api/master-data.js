import { api } from "./client.js";

export const SKILL_CATEGORIES = [
  { value: "language", label: "プログラミング言語" },
  { value: "framework", label: "フレームワーク" },
  { value: "database", label: "データベース" },
  { value: "cloud", label: "クラウド" },
];

export const masterDataApi = {
  async loadAll() {
    const [positions, jobTypes, skills] = await Promise.all([
      api.get("/positions"),
      api.get("/job-types"),
      api.get("/skills"),
    ]);
    return { positions, jobTypes, skills };
  },

  createPosition: (name) => api.post("/positions", { name }),
  renamePosition: (id, name) => api.patch(`/positions/${id}`, { name }),
  deletePosition: (id) => api.delete(`/positions/${id}`),

  createJobType: (name, isEngineer) =>
    api.post("/job-types", { name, is_engineer: isEngineer }),
  updateJobType: (id, name, isEngineer) =>
    api.patch(`/job-types/${id}`, { name, is_engineer: isEngineer }),
  deleteJobType: (id) => api.delete(`/job-types/${id}`),

  createSkill: (category, name) => api.post("/skills", { category, name }),
  renameSkill: (id, name) => api.patch(`/skills/${id}`, { name }),
  deleteSkill: (id) => api.delete(`/skills/${id}`),
};
