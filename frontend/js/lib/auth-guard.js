// ログイン状態と権限に応じて、表示してよい画面かどうかを判断し、必要なら移動させる。
// ※ 画面側のチェックは使いやすさのため。実際の権限チェックは API 側で行っている。

import { authApi } from "../api/auth.js";

export const PATHS = {
  login: "/login.html",
  setup: "/setup.html",
  masterHome: "/admin/users.html",
  generalHome: "/map.html",
};

export async function loadMe() {
  try {
    return await authApi.me();
  } catch (err) {
    if (err.status === 401) return null;
    throw err;
  }
}

export function needsSetup(me) {
  return me.role === "general" && (me.must_change_password || !me.profile_completed);
}

export function homePathFor(me) {
  if (me.role === "master") return PATHS.masterHome;
  if (needsSetup(me)) return PATHS.setup;
  return PATHS.generalHome;
}

/**
 * ログイン済みでなければログイン画面へ移動する。
 * @param {{ role?: "master" | "general", setupPage?: boolean }} options
 *   role: この画面を使える権限（省略時はどちらでも可）
 *   setupPage: 初回設定画面のときだけ true
 * @returns ログイン中のユーザー情報（移動する場合は解決しない）
 */
export async function requireAuth({ role, setupPage = false } = {}) {
  const me = await loadMe();
  if (!me) return redirect(PATHS.login);
  if (role && me.role !== role) return redirect(homePathFor(me));
  if (setupPage !== needsSetup(me)) return redirect(homePathFor(me));
  return me;
}

/** ログイン・新規登録画面用。すでにログインしていればホームへ移動する。 */
export async function redirectIfLoggedIn() {
  const me = await loadMe();
  if (me) redirect(homePathFor(me));
}

function redirect(path) {
  window.location.replace(path);
  return new Promise(() => {}); // 移動が終わるまで後続の処理を止める
}
