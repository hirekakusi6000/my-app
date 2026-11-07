import { usersApi } from "../api/users.js";
import { renderHeader } from "../components/app-header.js";
import { requireAuth } from "../lib/auth-guard.js";
import { clearErrors, handleSubmit } from "../lib/form.js";
import { generatePassword } from "../lib/password.js";
import { showToast } from "../lib/toast.js";
import { renderSampleDataBanner } from "../components/sample-data-banner.js";
import { setupCsvImportDialog } from "../components/csv-import-dialog.js";

const me = await requireAuth({ role: "master" });
renderHeader(document.getElementById("app-header"), me);

const rowsEl = document.getElementById("user-rows");
const countEl = document.getElementById("user-count");
const dialogs = {
  create: document.getElementById("create-dialog"),
  edit: document.getElementById("edit-dialog"),
  reset: document.getElementById("reset-dialog"),
  delete: document.getElementById("delete-dialog"),
  credential: document.getElementById("credential-dialog"),
};

/** 操作対象のユーザー（編集・リセット・削除のダイアログで使う） */
let target = null;

// ───────── 一覧 ─────────

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("ja-JP");
}

function statusLabel(user) {
  if (user.role === "master") return { text: "管理者", cls: "badge--muted" };
  if (user.must_change_password) return { text: "初回ログイン待ち", cls: "badge--warn" };
  if (!user.profile_completed) return { text: "プロフィール未登録", cls: "badge--warn" };
  return { text: "利用中", cls: "badge--ok" };
}

function cell(text, className) {
  const td = document.createElement("td");
  if (className) td.className = className;
  td.textContent = text;
  return td;
}

function actionButton(label, action, user, extraClass = "") {
  const b = document.createElement("button");
  b.type = "button";
  b.className = `button button--ghost button--small ${extraClass}`;
  b.textContent = label;
  b.addEventListener("click", () => openTargetDialog(action, user));
  return b;
}

function renderRows(users) {
  rowsEl.replaceChildren();
  for (const user of users) {
    const tr = document.createElement("tr");
    tr.append(
      cell(user.name ?? "—", user.name ? "" : "table__muted"),
      cell(user.email),
      cell(user.role === "master" ? "マスター" : "一般"),
    );

    const statusTd = document.createElement("td");
    const { text, cls } = statusLabel(user);
    const badge = document.createElement("span");
    badge.className = `badge ${cls}`;
    badge.textContent = text;
    statusTd.append(badge);
    tr.append(statusTd, cell(formatDate(user.created_at)));

    const actionsTd = document.createElement("td");
    actionsTd.className = "table__actions";
    if (user.role === "general") {
      actionsTd.append(
        actionButton("メール変更", "edit", user),
        actionButton("パスワードリセット", "reset", user),
        actionButton("削除", "delete", user, "button--danger-text"),
      );
    } else {
      actionsTd.append(cell("（あなた）", "table__muted").firstChild);
    }
    tr.append(actionsTd);
    rowsEl.append(tr);
  }
}

async function reload() {
  const data = await usersApi.list();
  renderRows(data.items);
  countEl.textContent = `（一般ユーザー ${data.general_user_count} / ${data.general_user_limit} 名）`;
  document.getElementById("open-create").disabled =
    data.general_user_count >= data.general_user_limit;
}

// ───────── ダイアログ共通 ─────────

for (const dialog of Object.values(dialogs)) {
  dialog.querySelectorAll("[data-close]").forEach((b) =>
    b.addEventListener("click", () => dialog.close()),
  );
  dialog.querySelectorAll("[data-generate]").forEach((b) =>
    b.addEventListener("click", () => {
      b.previousElementSibling.value = generatePassword();
    }),
  );
}

function openTargetDialog(action, user) {
  target = user;
  const dialog = dialogs[action];
  const form = dialog.querySelector("form");
  form.reset();
  clearErrors(form);
  dialog.querySelectorAll("[data-target-label]").forEach((el) => {
    el.textContent = user.name ? `${user.name}（${user.email}）` : user.email;
  });
  if (action === "edit") form.elements.email.value = user.email;
  if (action === "reset") form.elements.new_password.value = generatePassword();
  dialog.showModal();
}

function showCredential(title, email, password) {
  const d = dialogs.credential;
  d.querySelector("[data-title]").textContent = title;
  d.querySelector("[data-email]").textContent = email;
  d.querySelector("[data-password]").textContent = password;
  d.showModal();
}

dialogs.credential.querySelector("[data-copy]").addEventListener("click", async () => {
  const d = dialogs.credential;
  const text =
    `メールアドレス: ${d.querySelector("[data-email]").textContent}\n` +
    `初期パスワード: ${d.querySelector("[data-password]").textContent}`;
  try {
    await navigator.clipboard.writeText(text);
    showToast("コピーしました");
  } catch {
    showToast("コピーできませんでした。手動で控えてください", "error");
  }
});

// ───────── 作成 ─────────

document.getElementById("open-create").addEventListener("click", () => {
  const form = document.getElementById("create-form");
  form.reset();
  clearErrors(form);
  form.elements.initial_password.value = generatePassword();
  dialogs.create.showModal();
});

handleSubmit(document.getElementById("create-form"), async (data) => {
  const user = await usersApi.create(data.email.trim(), data.initial_password);
  dialogs.create.close();
  await reload();
  showCredential("ユーザーを作成しました", user.email, data.initial_password);
});

// ───────── メール変更・パスワードリセット・削除 ─────────

handleSubmit(document.getElementById("edit-form"), async (data) => {
  await usersApi.updateEmail(target.id, data.email.trim());
  dialogs.edit.close();
  await reload();
  showToast("メールアドレスを変更しました");
});

handleSubmit(document.getElementById("reset-form"), async (data) => {
  await usersApi.resetPassword(target.id, data.new_password);
  dialogs.reset.close();
  await reload();
  showCredential("パスワードをリセットしました", target.email, data.new_password);
});

handleSubmit(document.getElementById("delete-form"), async () => {
  await usersApi.remove(target.id);
  dialogs.delete.close();
  await reload();
  showToast("ユーザーを削除しました");
});

await reload();

// 何もない組織には、お試し用のサンプルデータを案内する
renderSampleDataBanner(document.getElementById("sample-banner"), { onCreated: reload });

// CSV で一括登録
const importDialog = setupCsvImportDialog(document.getElementById("import-dialog"), {
  onImported: reload,
});
document.getElementById("open-import").addEventListener("click", () => importDialog.open());
