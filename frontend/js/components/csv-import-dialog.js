// ユーザーの CSV 一括登録ダイアログ。
// ファイルを選ぶ → サーバーで内容を確認（dry_run）→ 問題がなければ登録 → 初期パスワードの一覧を保存、の順に進む。

import { usersApi } from "../api/users.js";
import { showToast } from "../lib/toast.js";

const TEMPLATE = "メールアドレス,初期パスワード\r\ntaro@example.com,\r\nhanako@example.com,\r\n";

/** 文字列を CSV ファイルとして保存させる（Excel で文字化けしないよう BOM を付ける） */
function downloadCsv(filename, text) {
  const blob = new Blob(["﻿", text], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function csvEscape(value) {
  const s = String(value ?? "");
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/**
 * @param {HTMLDialogElement} dialog
 * @param {{ onImported: () => void }} options
 */
export function setupCsvImportDialog(dialog, { onImported }) {
  const q = (sel) => dialog.querySelector(sel);
  const fileInput = q("[data-file]");
  const importButton = q("[data-import]");
  const downloadButton = q("[data-download]");
  let file = null;
  let created = [];

  function showStep(step) {
    q('[data-step="select"]').hidden = step !== "select";
    q('[data-step="preview"]').hidden = step === "select";
  }

  function reset() {
    file = null;
    created = [];
    fileInput.value = "";
    importButton.hidden = true;
    importButton.disabled = true;
    downloadButton.hidden = true;
    showStep("select");
  }

  function renderRows(result, { showPasswords }) {
    const tbody = q("[data-rows]");
    tbody.replaceChildren();
    for (const r of result.rows) {
      const tr = document.createElement("tr");
      const cells = [
        String(r.line),
        r.email || "（空欄）",
        showPasswords ? r.initial_password : r.password_provided ? "（CSV の値）" : "（自動で作成）",
        r.error ?? (showPasswords ? "登録しました" : "OK"),
      ];
      for (const [i, text] of cells.entries()) {
        const td = document.createElement("td");
        td.textContent = text;
        if (i === 2 && showPasswords) td.className = "mono";
        if (i === 3) td.className = r.error ? "text-danger" : "text-ok";
        tr.append(td);
      }
      tbody.append(tr);
    }
    const fileError = q("[data-file-error]");
    fileError.hidden = !result.error;
    fileError.textContent = result.error ?? "";
  }

  async function preview() {
    const result = await usersApi.importCsv(file, { dryRun: true });
    const errors = result.rows.filter((r) => r.error).length;
    const ok = !result.error && errors === 0;
    q("[data-summary]").textContent = ok
      ? `${result.rows.length}人を登録できます。内容を確認して「登録する」を押してください。`
      : `エラーがあるため登録できません（エラー ${errors} 行）。CSV を直してから、もう一度選んでください。`;
    renderRows(result, { showPasswords: false });
    importButton.hidden = false;
    importButton.disabled = !ok;
    showStep("preview");
  }

  fileInput.addEventListener("change", async () => {
    file = fileInput.files[0] ?? null;
    if (!file) return;
    try {
      await preview();
    } catch (err) {
      // ファイル全体の問題（文字コード・見出しなど）
      showToast(err.message, "error");
      reset();
    }
  });

  importButton.addEventListener("click", async () => {
    importButton.disabled = true;
    try {
      const result = await usersApi.importCsv(file, { dryRun: false });
      if (!result.created) {
        // 確認した後に状況が変わった場合（他の人が同じメールアドレスを登録したなど）
        renderRows(result, { showPasswords: false });
        q("[data-summary]").textContent = "状況が変わったため登録できませんでした。内容を確認してください。";
        return;
      }
      created = result.rows;
      renderRows(result, { showPasswords: true });
      q("[data-summary]").textContent =
        `${created.length}人を登録しました。初期パスワードはこの画面を閉じると再表示できないため、「結果を CSV で保存」してから本人に伝えてください。`;
      importButton.hidden = true;
      downloadButton.hidden = false;
      showToast(`${created.length}人を登録しました`);
      onImported();
    } catch (err) {
      showToast(err.message, "error");
      importButton.disabled = false;
    }
  });

  downloadButton.addEventListener("click", () => {
    const lines = ["メールアドレス,初期パスワード", ...created.map((r) => `${csvEscape(r.email)},${csvEscape(r.initial_password)}`)];
    downloadCsv("初期パスワード一覧.csv", `${lines.join("\r\n")}\r\n`);
  });

  q("[data-template]").addEventListener("click", (e) => {
    e.preventDefault();
    downloadCsv("ユーザー一括登録のひな形.csv", TEMPLATE);
  });

  q("[data-close]").addEventListener("click", () => {
    if (created.length && !confirm("初期パスワードの一覧を保存しましたか？\n閉じると再表示できません。")) return;
    dialog.close();
  });

  return {
    open() {
      reset();
      dialog.showModal();
    },
  };
}
