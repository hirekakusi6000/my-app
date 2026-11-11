// 組織の設定の API。通信の共通処理は、まだ移行していない frontend/js/api/client.js を使う。
import { api } from "@legacy/js/api/client.js";

import type { Organization } from "@/types/api";

export const organizationApi = {
  get: (): Promise<Organization> => api.get("/organization"),
  rename: (name: string): Promise<Organization> => api.patch("/organization", { name }),
  remove: (password: string, confirmName: string): Promise<null> =>
    api.delete("/organization", { password, confirm_name: confirmName }),
};
