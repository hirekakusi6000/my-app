// プロフィールの入力欄（初回設定とマイプロフィールで共通）。
// 役職・職種は候補から選ぶか、新しい名前を入力できる（<datalist>）。

const MAX_AVATAR_BYTES = 2 * 1024 * 1024;
const AVATAR_TYPES = ["image/png", "image/jpeg", "image/webp"];

function todayIso() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function fillDatalist(datalist, names) {
  datalist.replaceChildren(
    ...names.map((name) => {
      const option = document.createElement("option");
      option.value = name;
      return option;
    }),
  );
}

/**
 * @param {HTMLElement} container 入力欄を差し込む要素
 * @param {{ positions: any[], jobTypes: any[] }} masterData
 * @param {object | null} profile 既存のプロフィール（GET /me/profile）
 * @param {{ allowAvatarDelete?: boolean, onJobTypeChange?: (isEngineer: boolean) => void }} options
 */
export function renderProfileFields(container, masterData, profile, options = {}) {
  container.innerHTML = `
    <div class="avatar-field">
      <img class="avatar avatar--lg" data-avatar-preview alt="" hidden>
      <div class="avatar avatar--lg avatar--placeholder" data-avatar-placeholder>画像なし</div>
      <div class="field">
        <span class="field__label">プロフィール画像（任意）</span>
        <input type="file" name="avatar" accept="image/png,image/jpeg,image/webp">
        <span class="field__hint">PNG / JPEG / WebP、2MBまで</span>
        <span class="field__error" data-error-for="avatar"></span>
        <button type="button" class="button button--ghost button--small" data-avatar-delete hidden>画像を削除</button>
      </div>
    </div>

    <label class="field">
      <span class="field__label">名前</span>
      <input class="field__input" type="text" name="name" maxlength="50" required>
      <span class="field__error" data-error-for="name"></span>
    </label>

    <label class="field">
      <span class="field__label">生年月日</span>
      <input class="field__input" type="date" name="birth_date" min="1900-01-01" required>
      <span class="field__hint">他の人には年齢だけが表示されます</span>
      <span class="field__error" data-error-for="birth_date"></span>
    </label>

    <div class="field-row">
      <label class="field">
        <span class="field__label">役職</span>
        <input class="field__input" type="text" name="position_name" maxlength="50" list="position-options" placeholder="選択または入力">
        <datalist id="position-options"></datalist>
        <span class="field__error" data-error-for="position_name"></span>
      </label>
      <label class="field">
        <span class="field__label">職種</span>
        <input class="field__input" type="text" name="job_type_name" maxlength="50" list="job-type-options" placeholder="選択または入力">
        <datalist id="job-type-options"></datalist>
        <span class="field__hint" data-engineer-hint hidden>エンジニアの職種です。技術スキルを登録できます。</span>
        <span class="field__error" data-error-for="job_type_name"></span>
      </label>
    </div>
  `;

  const q = (sel) => container.querySelector(sel);
  fillDatalist(q("#position-options"), masterData.positions.map((p) => p.name));
  fillDatalist(q("#job-type-options"), masterData.jobTypes.map((j) => j.name));
  q('[name="birth_date"]').max = todayIso();

  const preview = q("[data-avatar-preview]");
  const placeholder = q("[data-avatar-placeholder]");
  const deleteButton = q("[data-avatar-delete]");
  const fileInput = q('[name="avatar"]');
  let deleteAvatar = false;

  function showAvatar(url) {
    preview.hidden = !url;
    placeholder.hidden = Boolean(url);
    if (url) preview.src = url;
    deleteButton.hidden = !(options.allowAvatarDelete && url && !fileInput.files.length);
  }

  if (profile) {
    q('[name="name"]').value = profile.name;
    q('[name="birth_date"]').value = profile.birth_date;
    q('[name="position_name"]').value = profile.position ?? "";
    q('[name="job_type_name"]').value = profile.job_type ?? "";
  }
  showAvatar(profile?.avatar_url ?? null);

  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    q('[data-error-for="avatar"]').textContent = "";
    if (!file) return showAvatar(profile?.avatar_url ?? null);
    deleteAvatar = false;
    showAvatar(URL.createObjectURL(file));
  });

  deleteButton.addEventListener("click", () => {
    deleteAvatar = true;
    showAvatar(null);
  });

  // 職種がエンジニアかどうか（候補にない新しい名前はエンジニア以外として扱う）
  function isEngineer() {
    const name = q('[name="job_type_name"]').value.trim().toLowerCase();
    return masterData.jobTypes.some((j) => j.is_engineer && j.name.toLowerCase() === name);
  }

  const jobTypeInput = q('[name="job_type_name"]');
  const updateEngineerHint = () => {
    q("[data-engineer-hint]").hidden = !isEngineer();
    options.onJobTypeChange?.(isEngineer());
  };
  jobTypeInput.addEventListener("input", updateEngineerHint);
  updateEngineerHint();

  return {
    isEngineer,
    /** 入力内容を検証し、問題があればエラーを表示して null を返す */
    getValues() {
      const file = fileInput.files[0] ?? null;
      if (file && !AVATAR_TYPES.includes(file.type)) {
        q('[data-error-for="avatar"]').textContent = "PNG / JPEG / WebP の画像を選んでください";
        return null;
      }
      if (file && file.size > MAX_AVATAR_BYTES) {
        q('[data-error-for="avatar"]').textContent = "画像のサイズは2MBまでです";
        return null;
      }
      return {
        name: q('[name="name"]').value.trim(),
        birthDate: q('[name="birth_date"]').value,
        positionName: q('[name="position_name"]').value.trim(),
        jobTypeName: jobTypeInput.value.trim(),
        avatarFile: file,
        deleteAvatar,
      };
    },
  };
}
