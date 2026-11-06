// 共通ヘッダー（組織名・ナビゲーション・ログイン中のユーザー・ログアウト）。

import { authApi } from "../api/auth.js";
import { PATHS } from "../lib/auth-guard.js";

const NAV = {
  master: [
    { href: "/admin/users.html", label: "ユーザー管理" },
    { href: "/admin/master-data.html", label: "候補の管理" },
    { href: "/map.html", label: "マップ" },
  ],
  general: [
    { href: "/map.html", label: "マップ" },
    { href: "/profile.html", label: "プロフィール" },
  ],
};

/**
 * @param {HTMLElement} container
 * @param {object} me GET /me の結果
 * @param {{ nav?: boolean }} options nav=false でナビゲーションを表示しない（初回設定画面など）
 */
export function renderHeader(container, me, { nav = true } = {}) {
  container.className = "app-header";
  container.innerHTML = `
    <div class="app-header__brand"></div>
    <nav class="app-header__nav"></nav>
    <div class="app-header__user">
      <span class="app-header__email"></span>
      <button type="button" class="button button--ghost" data-logout>ログアウト</button>
    </div>
  `;
  // ユーザーが入力した文字列は textContent で入れる（HTML として解釈させない）
  container.querySelector(".app-header__brand").textContent = me.organization.name;
  container.querySelector(".app-header__email").textContent = me.email;

  if (nav) {
    const navEl = container.querySelector(".app-header__nav");
    for (const item of NAV[me.role] ?? []) {
      const a = document.createElement("a");
      a.href = item.href;
      a.textContent = item.label;
      if (window.location.pathname === item.href) a.setAttribute("aria-current", "page");
      navEl.append(a);
    }
  }

  container.querySelector("[data-logout]").addEventListener("click", async () => {
    try {
      await authApi.logout();
    } finally {
      window.location.replace(PATHS.login);
    }
  });
}
