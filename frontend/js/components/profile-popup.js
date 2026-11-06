// 従業員のプロフィールをポップアップ（ダイアログ）で表示する。

import { SKILL_CATEGORIES } from "../api/master-data.js";
import { profileApi } from "../api/profile.js";
import { STATUS_LABELS } from "./map-renderer.js";

let dialog;

function ensureDialog() {
  if (dialog) return dialog;
  dialog = document.createElement("dialog");
  dialog.className = "dialog profile-popup";
  dialog.innerHTML = `
    <div class="profile-popup__head">
      <img class="avatar avatar--lg" data-avatar alt="">
      <div class="avatar avatar--lg avatar--placeholder" data-avatar-placeholder></div>
      <div>
        <h2 class="dialog__title" data-name></h2>
        <p class="profile-popup__meta" data-meta></p>
        <span class="status-badge" data-status></span>
      </div>
    </div>
    <p class="profile-popup__comment" data-comment></p>
    <div data-skills></div>
    <div class="dialog__actions">
      <button type="button" class="button button--ghost" data-close>閉じる</button>
    </div>
  `;
  dialog.querySelector("[data-close]").addEventListener("click", () => dialog.close());
  // 背景をクリックしたら閉じる
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close();
  });
  document.body.append(dialog);
  return dialog;
}

function text(sel, value) {
  dialog.querySelector(sel).textContent = value;
}

/** @param {number} userId */
export async function openProfilePopup(userId) {
  const d = ensureDialog();
  text("[data-name]", "読み込み中...");
  text("[data-meta]", "");
  text("[data-comment]", "");
  d.querySelector("[data-skills]").replaceChildren();
  d.showModal();

  let p;
  try {
    p = await profileApi.get(userId);
  } catch (err) {
    text("[data-name]", "プロフィールを表示できません");
    text("[data-meta]", err.message);
    return;
  }

  const img = d.querySelector("[data-avatar]");
  const placeholder = d.querySelector("[data-avatar-placeholder]");
  img.hidden = !p.avatar_url;
  placeholder.hidden = Boolean(p.avatar_url);
  if (p.avatar_url) img.src = p.avatar_url;
  else placeholder.textContent = p.name.charAt(0);

  text("[data-name]", p.name);
  text(
    "[data-meta]",
    [`${p.age}歳`, p.position, p.job_type].filter(Boolean).join(" ・ "),
  );

  const status = p.presence?.status ?? "not_working";
  const badge = d.querySelector("[data-status]");
  badge.className = `status-badge status-badge--${status}`;
  badge.textContent = STATUS_LABELS[status];

  const comment = p.presence?.comment;
  const commentEl = d.querySelector("[data-comment]");
  commentEl.hidden = !comment;
  commentEl.textContent = comment ? `💬 ${comment}` : "";

  const skillsEl = d.querySelector("[data-skills]");
  if (p.is_engineer && p.skills.length) {
    for (const { value, label } of SKILL_CATEGORIES) {
      const items = p.skills.filter((s) => s.category === value);
      if (!items.length) continue;
      const row = document.createElement("div");
      row.className = "profile-popup__skills";
      const heading = document.createElement("span");
      heading.className = "profile-popup__skill-category";
      heading.textContent = label;
      row.append(heading);
      for (const s of items) {
        const chip = document.createElement("span");
        chip.className = "chip";
        chip.textContent = `${s.name} ${s.years}年`;
        row.append(chip);
      }
      skillsEl.append(row);
    }
  }
}
