<script setup lang="ts">
/**
 * 組織の設定（マスターのみ）：組織名の変更と、組織の削除。
 * 見た目と動きは Vue に移行する前（frontend/admin/organization.html）と同じ。
 */
import { computed, onMounted, ref, useTemplateRef } from "vue";

import { PATHS } from "@legacy/js/lib/auth-guard.js";
import { showToast } from "@legacy/js/lib/toast.js";

import { organizationApi } from "@/api/organization";
import { type FormErrors, toFormErrors } from "@/lib/errors";
import type { Organization } from "@/types/api";

const emit = defineEmits<{
  /** 組織名を変更したとき（ヘッダーの表示を更新するため） */
  renamed: [name: string];
}>();

const noErrors = (): FormErrors => ({ fields: {}, form: "" });

const organization = ref<Organization | null>(null);
const createdAt = computed(() =>
  organization.value ? new Date(organization.value.created_at).toLocaleDateString("ja-JP") : "",
);

onMounted(async () => {
  organization.value = await organizationApi.get();
  name.value = organization.value.name;
});

// ───────── 組織名の変更 ─────────

const name = ref("");
const renameErrors = ref(noErrors());
const saving = ref(false);

async function rename() {
  renameErrors.value = noErrors();
  saving.value = true;
  try {
    organization.value = await organizationApi.rename(name.value.trim());
    name.value = organization.value.name;
    emit("renamed", organization.value.name);
    showToast("組織名を変更しました");
  } catch (err) {
    renameErrors.value = toFormErrors(err, { name: "組織名は1〜100文字で入力してください" });
  } finally {
    saving.value = false;
  }
}

// ───────── 組織の削除 ─────────

const deleteDialog = useTemplateRef<HTMLDialogElement>("deleteDialog");
const confirmName = ref("");
const password = ref("");
const deleteErrors = ref(noErrors());
const deleting = ref(false);

// 組織名を正しく入力するまで、削除ボタンを押せないようにする
const canDelete = computed(
  () =>
    !deleting.value &&
    password.value.length > 0 &&
    confirmName.value.trim() === organization.value?.name,
);

function openDelete() {
  confirmName.value = "";
  password.value = "";
  deleteErrors.value = noErrors();
  deleteDialog.value?.showModal();
}

async function remove() {
  if (!canDelete.value) return;
  deleteErrors.value = noErrors();
  deleting.value = true;
  try {
    await organizationApi.remove(password.value, confirmName.value);
    deleteDialog.value?.close();
    alert("組織を削除しました。ご利用ありがとうございました。");
    window.location.replace(PATHS.login);
  } catch (err) {
    deleteErrors.value = toFormErrors(err);
    deleting.value = false;
  }
}
</script>

<template>
  <main class="page page--narrow">
    <h1 class="page__title">組織の設定</h1>

    <section class="panel">
      <h2 class="panel__title">組織名</h2>
      <form id="rename-form" class="form" novalidate @submit.prevent="rename">
        <div v-if="renameErrors.form" class="alert alert--error">{{ renameErrors.form }}</div>
        <label class="field">
          <span class="field__label">組織名</span>
          <input v-model="name" class="field__input" type="text" name="name" maxlength="100" required>
          <span class="field__error">{{ renameErrors.fields.name }}</span>
        </label>
        <p v-if="createdAt" class="field__hint">作成日：{{ createdAt }}</p>
        <div class="panel__actions">
          <button type="submit" class="button" :disabled="saving">保存する</button>
        </div>
      </form>
    </section>

    <section class="panel panel--danger">
      <h2 class="panel__title">組織の削除</h2>
      <p class="dialog__text">
        組織と、そこに含まれる<strong>すべてのデータ</strong>（従業員のアカウント・プロフィール・画像・スキル・在席状態・フロア・部屋・マップ・候補の一覧）を完全に削除します。
        <strong>元に戻すことはできません。</strong>
      </p>
      <div class="panel__actions">
        <button type="button" class="button button--danger" @click="openDelete">組織を削除する</button>
      </div>
    </section>
  </main>

  <dialog ref="deleteDialog" class="dialog">
    <form id="delete-form" class="form" novalidate @submit.prevent="remove">
      <h2 class="dialog__title">組織を完全に削除する</h2>
      <p class="dialog__text">
        確認のため、組織名「<strong>{{ organization?.name }}</strong>」とあなたのパスワードを入力してください。
      </p>
      <div v-if="deleteErrors.form" class="alert alert--error">{{ deleteErrors.form }}</div>
      <label class="field">
        <span class="field__label">組織名</span>
        <input v-model="confirmName" class="field__input" type="text" name="confirm_name" autocomplete="off" required>
      </label>
      <label class="field">
        <span class="field__label">パスワード</span>
        <input v-model="password" class="field__input" type="password" name="password" autocomplete="current-password" required>
      </label>
      <div class="dialog__actions">
        <button type="button" class="button button--ghost" @click="deleteDialog?.close()">キャンセル</button>
        <button type="submit" class="button button--danger" :disabled="!canDelete">完全に削除する</button>
      </div>
    </form>
  </dialog>
</template>
