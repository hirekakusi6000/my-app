/**
 * Vue の画面のビルド設定。
 *
 * 画面は1枚ずつ Vue に移行する。移行した画面の HTML は web/ に置き、ここの PAGES に追加する。
 * ビルドした結果（web/dist）は FastAPI が配信し、まだ移行していない画面は frontend/ から配信する。
 * どちらも同じ URL（例: /admin/organization.html）で開ける。
 */
import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

/** Vue に移行した画面（出力先のパス → web/ の中の HTML） */
const PAGES: Record<string, string> = {
  "admin/organization": "admin/organization.html",
};

const root = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  root,
  base: "/",
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      // まだ移行していない共通の部品（ヘッダー・API の呼び出しなど）を Vue の画面からも使う
      "@legacy": fileURLToPath(new URL("../frontend", import.meta.url)),
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    // 画面のスクリプトは最上位で await を使うため
    target: "es2022",
    // frontend/ の css・js と名前がぶつからないよう、出力をまとめる
    assetsDir: "assets/vue",
    rollupOptions: {
      input: Object.fromEntries(
        Object.entries(PAGES).map(([name, html]) => [name, fileURLToPath(new URL(html, import.meta.url))]),
      ),
    },
  },
});
