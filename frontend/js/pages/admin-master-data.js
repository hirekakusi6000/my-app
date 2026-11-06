import { ApiError } from "../api/client.js";
import { masterDataApi, SKILL_CATEGORIES } from "../api/master-data.js";
import { renderHeader } from "../components/app-header.js";
import { requireAuth } from "../lib/auth-guard.js";
import { clearErrors, handleSubmit } from "../lib/form.js";
import { showToast } from "../lib/toast.js";

const me = await requireAuth({ role: "master" });
renderHeader(document.getElementById("app-header"), me);

const CATEGORY_LABEL = Object.fromEntries(SKILL_CATEGORIES.map((c) => [c.value, c.label]));

// タブごとの API 呼び出しの違いをここにまとめる
const TABS = {
  positions: {
    create: (form) => masterDataApi.createPosition(form.name),
    rename: (item, name) => masterDataApi.renamePosition(item.id, name),
    remove: (item) => masterDataApi.deletePosition(item.id),
    deleteNote: "この役職を設定している従業員は「役職なし」になります。",
  },
  jobTypes: {
    create: (form) => masterDataApi.createJobType(form.name, form.is_engineer === "on"),
    rename: (item, name) => masterDataApi.updateJobType(item.id, name, item.is_engineer),
    remove: (item) => masterDataApi.deleteJobType(item.id),
    deleteNote: "この職種を設定している従業員は「職種なし」になります。",
  },
  skills: {
    create: (form) => masterDataApi.createSkill(form.category, form.name),
    rename: (item, name) => masterDataApi.renameSkill(item.id, name),
    remove: (item) => masterDataApi.deleteSkill(item.id),
    deleteNote: "このスキルを登録している従業員からも削除されます。",
  },
};

let data = await masterDataApi.loadAll();
let currentTab = "positions";

const listEl = document.getElementById("item-list");
const addForm = document.getElementById("add-form");
const addError = document.getElementById("add-error");
const skillFilter = document.getElementById("skill-filter");

// スキルの分類の選択肢
addForm.elements.category.append(
  ...SKILL_CATEGORIES.map((c) => new Option(c.label, c.value)),
);
skillFilter.append(
  new Option("すべて", ""),
  ...SKILL_CATEGORIES.map((c) => new Option(c.label, c.value)),
);
skillFilter.addEventListener("change", renderList);

// ───────── タブ ─────────

document.querySelectorAll(".tabs__tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    currentTab = tab.dataset.tab;
    document.querySelectorAll(".tabs__tab").forEach((t) =>
      t.setAttribute("aria-selected", String(t === tab)),
    );
    document.querySelectorAll("[data-only]").forEach((el) => {
      el.hidden = el.dataset.only !== currentTab;
    });
    addForm.reset();
    addError.hidden = true;
    renderList();
  });
});

// ───────── 一覧 ─────────

function itemsOfCurrentTab() {
  const items = data[currentTab];
  if (currentTab === "skills" && skillFilter.value) {
    return items.filter((s) => s.category === skillFilter.value);
  }
  return items;
}

function button(label, onClick, extra = "") {
  const b = document.createElement("button");
  b.type = "button";
  b.className = `button button--ghost button--small ${extra}`;
  b.textContent = label;
  b.addEventListener("click", onClick);
  return b;
}

function renderList() {
  const items = itemsOfCurrentTab();
  listEl.replaceChildren();
  if (items.length === 0) {
    const li = document.createElement("li");
    li.className = "item-list__empty";
    li.textContent = "登録されていません";
    listEl.append(li);
    return;
  }
  for (const item of items) {
    const li = document.createElement("li");
    li.className = "item-list__item";

    const name = document.createElement("span");
    name.className = "item-list__name";
    name.textContent = item.name;
    li.append(name);

    if (currentTab === "skills") {
      const tag = document.createElement("span");
      tag.className = "badge badge--muted";
      tag.textContent = CATEGORY_LABEL[item.category];
      li.append(tag);
    }

    if (currentTab === "jobTypes") {
      const label = document.createElement("label");
      label.className = "checkbox";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = item.is_engineer;
      checkbox.addEventListener("change", async () => {
        try {
          await masterDataApi.updateJobType(item.id, item.name, checkbox.checked);
          await reload();
          showToast(`「${item.name}」を${checkbox.checked ? "エンジニア" : "エンジニア以外"}にしました`);
        } catch (err) {
          checkbox.checked = !checkbox.checked;
          showToast(err.message, "error");
        }
      });
      label.append(checkbox, " エンジニア");
      li.append(label);
    }

    const actions = document.createElement("span");
    actions.className = "item-list__actions";
    actions.append(
      button("名前変更", () => openRename(item)),
      button("削除", () => removeItem(item), "button--danger-text"),
    );
    li.append(actions);
    listEl.append(li);
  }
}

async function reload() {
  data = await masterDataApi.loadAll();
  renderList();
}

// ───────── 追加・名前変更・削除 ─────────

addForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  addError.hidden = true;
  const form = Object.fromEntries(new FormData(addForm));
  form.name = (form.name ?? "").trim();
  if (!form.name) {
    addError.textContent = "名前を入力してください";
    addError.hidden = false;
    return;
  }
  try {
    await TABS[currentTab].create(form);
    addForm.elements.name.value = "";
    await reload();
    showToast(`「${form.name}」を追加しました`);
  } catch (err) {
    addError.textContent = err instanceof ApiError ? err.message : "追加できませんでした";
    addError.hidden = false;
  }
});

const renameDialog = document.getElementById("rename-dialog");
const renameForm = document.getElementById("rename-form");
let renameTarget = null;

renameDialog.querySelector("[data-close]").addEventListener("click", () => renameDialog.close());

function openRename(item) {
  renameTarget = item;
  clearErrors(renameForm);
  renameForm.elements.name.value = item.name;
  renameDialog.showModal();
}

handleSubmit(renameForm, async ({ name }) => {
  await TABS[currentTab].rename(renameTarget, name.trim());
  renameDialog.close();
  await reload();
  showToast("名前を変更しました");
});

async function removeItem(item) {
  if (!confirm(`「${item.name}」を削除しますか？\n${TABS[currentTab].deleteNote}`)) return;
  try {
    await TABS[currentTab].remove(item);
    await reload();
    showToast(`「${item.name}」を削除しました`);
  } catch (err) {
    showToast(err.message, "error");
  }
}

renderList();
