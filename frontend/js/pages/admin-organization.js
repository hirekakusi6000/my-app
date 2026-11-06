import { organizationApi } from "../api/organization.js";
import { renderHeader } from "../components/app-header.js";
import { PATHS, requireAuth } from "../lib/auth-guard.js";
import { clearErrors, handleSubmit } from "../lib/form.js";
import { showToast } from "../lib/toast.js";

const me = await requireAuth({ role: "master" });
const header = document.getElementById("app-header");
renderHeader(header, me);

let organization = await organizationApi.get();

const renameForm = document.getElementById("rename-form");
const deleteDialog = document.getElementById("delete-dialog");
const deleteForm = document.getElementById("delete-form");
const submitDelete = deleteForm.querySelector("[data-submit]");

function render() {
  renameForm.elements.name.value = organization.name;
  const created = new Date(organization.created_at).toLocaleDateString("ja-JP");
  document.getElementById("created-at").textContent = `作成日：${created}`;
  deleteDialog.querySelector("[data-org-name]").textContent = organization.name;
}

render();

// ───────── 組織名の変更 ─────────

handleSubmit(renameForm, async ({ name }) => {
  organization = await organizationApi.rename(name.trim());
  render();
  // ヘッダーの組織名も更新する
  renderHeader(header, { ...me, organization: { ...me.organization, name: organization.name } });
  showToast("組織名を変更しました");
});

// ───────── 組織の削除 ─────────

document.getElementById("open-delete").addEventListener("click", () => {
  deleteForm.reset();
  clearErrors(deleteForm);
  submitDelete.disabled = true;
  deleteDialog.showModal();
});

deleteDialog.querySelector("[data-close]").addEventListener("click", () => deleteDialog.close());

// 組織名を正しく入力するまで、削除ボタンを押せないようにする
deleteForm.addEventListener("input", () => {
  const { confirm_name: name, password } = deleteForm.elements;
  submitDelete.disabled = !(name.value.trim() === organization.name && password.value);
});

handleSubmit(deleteForm, async ({ confirm_name: confirmName, password }) => {
  await organizationApi.remove(password, confirmName);
  deleteDialog.close();
  alert("組織を削除しました。ご利用ありがとうございました。");
  window.location.replace(PATHS.login);
});
