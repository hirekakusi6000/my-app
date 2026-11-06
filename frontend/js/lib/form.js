// フォームの送信とエラー表示の共通処理。

import { ApiError } from "../api/client.js";

const FIELD_LABELS = {
  email: "メールアドレスの形式が正しくありません",
  password: "パスワードは8〜128文字で入力してください",
  new_password: "パスワードは8〜128文字で入力してください",
  initial_password: "パスワードは8〜128文字で入力してください",
  organization_name: "組織名は1〜100文字で入力してください",
  name: "1〜50文字で入力してください",
  birth_date: "生年月日を入力してください",
  position_name: "50文字以内で入力してください",
  job_type_name: "50文字以内で入力してください",
};

export function clearErrors(form) {
  form.querySelectorAll("[data-error-for]").forEach((el) => (el.textContent = ""));
  const alert = form.querySelector("[data-form-error]");
  if (alert) {
    alert.textContent = "";
    alert.hidden = true;
  }
}

export function showFormError(form, message) {
  const alert = form.querySelector("[data-form-error]");
  alert.textContent = message;
  alert.hidden = false;
}

function showFieldError(form, field, message) {
  const el = form.querySelector(`[data-error-for="${field}"]`);
  if (!el) return false;
  el.textContent = message;
  return true;
}

/** API のエラーを、項目ごとのエラーかフォーム全体のエラーとして表示する。 */
export function showApiError(form, err) {
  if (err instanceof ApiError && err.code === "VALIDATION_ERROR" && err.errors.length) {
    let shownAll = true;
    for (const { field } of err.errors) {
      const shown = showFieldError(form, field, FIELD_LABELS[field] ?? "入力内容を確認してください");
      shownAll &&= shown;
    }
    if (!shownAll) showFormError(form, err.message);
    return;
  }
  showFormError(form, err instanceof ApiError ? err.message : "通信に失敗しました。時間をおいて再度お試しください");
}

/**
 * フォームの送信処理をまとめて設定する（二重送信の防止とエラー表示）。
 * @param {HTMLFormElement} form
 * @param {(data: Record<string, string>) => Promise<void>} onSubmit
 */
export function handleSubmit(form, onSubmit) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrors(form);
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
      await onSubmit(Object.fromEntries(new FormData(form)));
    } catch (err) {
      showApiError(form, err);
    } finally {
      button.disabled = false;
    }
  });
}
