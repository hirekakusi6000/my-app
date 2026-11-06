import { troublesApi } from "../api/troubles.js";
import { renderHeader } from "../components/app-header.js";
import { openProfilePopup } from "../components/profile-popup.js";
import { requireAuth } from "../lib/auth-guard.js";
import { clearErrors, handleSubmit } from "../lib/form.js";
import { showToast } from "../lib/toast.js";

const me = await requireAuth();
renderHeader(document.getElementById("app-header"), me);
const isGeneral = me.role === "general";

const listEl = document.getElementById("list");
const dialog = document.getElementById("edit-dialog");
const form = document.getElementById("edit-form");

let troubles = [];
let currentTab = "open";
let editing = null;

// 一般ユーザーだけが登録でき、「自分の」タブを使える
document.getElementById("open-create").hidden = !isGeneral;
document.querySelector('[data-tab="mine"]').hidden = !isGeneral;

// ───────── 表示 ─────────

function formatDate(iso) {
  return new Date(iso).toLocaleString("ja-JP", {
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function el(tag, className, text) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text !== undefined) e.textContent = text;
  return e;
}

function filtered() {
  if (currentTab === "mine") return troubles.filter((t) => t.is_mine);
  return troubles.filter((t) => t.status === currentTab);
}

function renderCounts() {
  const counts = {
    open: troubles.filter((t) => t.status === "open").length,
    resolved: troubles.filter((t) => t.status === "resolved").length,
    mine: troubles.filter((t) => t.is_mine).length,
  };
  for (const [key, n] of Object.entries(counts)) {
    document.querySelector(`[data-count="${key}"]`).textContent = `(${n})`;
  }
}

function render() {
  renderCounts();
  const items = filtered();
  listEl.replaceChildren();
  if (!items.length) {
    const empty = el("div", "empty-state");
    empty.append(
      el("p", "", currentTab === "open" ? "未解決の困りごとはありません 🎉" : "まだありません"),
    );
    listEl.append(empty);
    return;
  }
  for (const t of items) listEl.append(renderCard(t));
}

function renderCard(t) {
  const card = el("article", `trouble trouble--${t.status}`);

  const head = el("div", "trouble__head");
  const author = el("button", "trouble__author");
  author.type = "button";
  if (t.author_avatar_url) {
    const img = el("img", "avatar avatar--sm");
    img.src = t.author_avatar_url;
    img.alt = "";
    author.append(img);
  } else {
    author.append(el("span", "avatar avatar--sm avatar--placeholder", (t.author_name ?? "?").charAt(0)));
  }
  author.append(el("span", "", t.author_name ?? "名前未登録"));
  author.addEventListener("click", () => openProfilePopup(t.user_id));

  const badge = el(
    "span",
    `badge ${t.status === "open" ? "badge--warn" : "badge--ok"}`,
    t.status === "open" ? "未解決" : "解決済み",
  );
  head.append(author, badge, el("span", "trouble__date", formatDate(t.updated_at)));

  card.append(head, el("h3", "trouble__title", t.title));
  if (t.body) card.append(el("p", "trouble__body", t.body));

  const actions = el("div", "trouble__actions");
  if (t.is_mine) {
    actions.append(
      button(t.status === "open" ? "解決済みにする" : "未解決に戻す", () => toggleStatus(t)),
      button("編集", () => openDialog(t)),
    );
  }
  if (t.is_mine || me.role === "master") {
    actions.append(button("削除", () => remove(t), "button--danger-text"));
  }
  if (actions.childElementCount) card.append(actions);
  return card;
}

function button(label, onClick, extra = "") {
  const b = el("button", `button button--ghost button--small ${extra}`, label);
  b.type = "button";
  b.addEventListener("click", onClick);
  return b;
}

async function reload() {
  troubles = await troublesApi.list();
  render();
}

// ───────── タブ ─────────

document.querySelectorAll(".tabs__tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    currentTab = tab.dataset.tab;
    document.querySelectorAll(".tabs__tab").forEach((t) =>
      t.setAttribute("aria-selected", String(t === tab)),
    );
    render();
  });
});

// ───────── 登録・編集・状態変更・削除 ─────────

dialog.querySelector("[data-close]").addEventListener("click", () => dialog.close());
document.getElementById("open-create").addEventListener("click", () => openDialog(null));

function openDialog(trouble) {
  editing = trouble;
  form.reset();
  clearErrors(form);
  dialog.querySelector("[data-title]").textContent = trouble ? "困りごとを編集" : "困りごとを登録";
  if (trouble) {
    form.elements.title.value = trouble.title;
    form.elements.body.value = trouble.body;
  }
  dialog.showModal();
}

handleSubmit(form, async ({ title, body }) => {
  if (editing) await troublesApi.update(editing.id, { title, body });
  else await troublesApi.create(title, body);
  dialog.close();
  if (!editing) {
    currentTab = "open";
    document.querySelectorAll(".tabs__tab").forEach((t) =>
      t.setAttribute("aria-selected", String(t.dataset.tab === "open")),
    );
  }
  await reload();
  showToast(editing ? "困りごとを更新しました" : "困りごとを登録しました");
});

async function toggleStatus(t) {
  const status = t.status === "open" ? "resolved" : "open";
  try {
    await troublesApi.update(t.id, { status });
    await reload();
    showToast(status === "resolved" ? "解決済みにしました" : "未解決に戻しました");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function remove(t) {
  if (!confirm(`「${t.title}」を削除しますか？`)) return;
  try {
    await troublesApi.remove(t.id);
    await reload();
    showToast("削除しました");
  } catch (err) {
    showToast(err.message, "error");
  }
}

await reload();
