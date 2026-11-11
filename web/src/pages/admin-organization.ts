// 組織の設定の画面の入口。ログインと権限を確認してから、Vue の画面を表示する。
import "@legacy/css/base.css";
import "@legacy/css/components.css";

import { createApp } from "vue";

import { renderHeader } from "@legacy/js/components/app-header.js";
import { requireAuth } from "@legacy/js/lib/auth-guard.js";

import AdminOrganization from "@/pages/AdminOrganization.vue";
import type { Me } from "@/types/api";

const me = (await requireAuth({ role: "master" })) as Me;
const header = document.getElementById("app-header") as HTMLElement;
renderHeader(header, me);

createApp(AdminOrganization, {
  // 組織名を変えたら、ヘッダーの組織名も変える
  onRenamed: (name: string) =>
    renderHeader(header, { ...me, organization: { ...me.organization, name } }),
}).mount("#app");
