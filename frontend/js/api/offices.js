import { api } from "./client.js";

export const officesApi = {
  listFloors: () => api.get("/floors"),
  createFloor: (name) => api.post("/floors", { name }),
  updateFloor: (id, fields) => api.patch(`/floors/${id}`, fields),
  deleteFloor: (id) => api.delete(`/floors/${id}`),

  createRoom: (floorId, { name, width, height }) =>
    api.post(`/floors/${floorId}/rooms`, { name, width, height }),
  updateRoom: (id, fields) => api.patch(`/rooms/${id}`, fields),
  deleteRoom: (id) => api.delete(`/rooms/${id}`),

  getLayout: (roomId) => api.get(`/rooms/${roomId}/layout`),
  saveLayout: (roomId, furniture) => api.put(`/rooms/${roomId}/layout`, { furniture }),
  getOccupancy: (roomId) => api.get(`/rooms/${roomId}/occupancy`),
};
