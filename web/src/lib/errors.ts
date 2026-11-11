// API のエラーを、項目ごとのエラーとフォーム全体のエラーに分ける。
import { ApiError } from "@legacy/js/api/client.js";

import type { FieldError } from "@/types/api";

export interface FormErrors {
  /** 項目名 → 表示するメッセージ */
  fields: Record<string, string>;
  /** 項目に結び付かないエラー（フォームの上に表示する） */
  form: string;
}

/**
 * @param labels 入力チェックのエラーのとき、項目ごとに表示する分かりやすいメッセージ
 */
export function toFormErrors(err: unknown, labels: Record<string, string> = {}): FormErrors {
  if (err instanceof ApiError && err.code === "VALIDATION_ERROR") {
    const fields: Record<string, string> = {};
    for (const { field } of err.errors as FieldError[]) {
      fields[field] = labels[field] ?? "入力内容を確認してください";
    }
    return { fields, form: Object.keys(fields).length ? "" : err.message };
  }
  return {
    fields: {},
    form: err instanceof ApiError ? err.message : "通信に失敗しました。時間をおいて再度お試しください",
  };
}
