import { authApi } from "../api/auth.js";
import { masterDataApi } from "../api/master-data.js";
import { profileApi } from "../api/profile.js";
import { renderHeader } from "../components/app-header.js";
import { renderProfileFields } from "../components/profile-fields.js";
import { renderSkillsEditor } from "../components/skills-editor.js";
import { requireAuth } from "../lib/auth-guard.js";
import { handleSubmit, showFormError } from "../lib/form.js";
import { showToast } from "../lib/toast.js";

const me = await requireAuth({ role: "general", setupPage: true });
renderHeader(document.getElementById("app-header"), me, { nav: false });

const STEPS = ["password", "profile", "skills", "seat"];

function showStep(step) {
  document.querySelectorAll(".steps li").forEach((li) => {
    const index = STEPS.indexOf(li.dataset.step);
    li.toggleAttribute("data-done", index < STEPS.indexOf(step));
    if (li.dataset.step === step) li.setAttribute("aria-current", "step");
    else li.removeAttribute("aria-current");
  });
  document.querySelectorAll("[data-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.panel !== step;
  });
}

// ───────── ① パスワード変更 ─────────

const passwordForm = document.getElementById("password-form");
handleSubmit(passwordForm, async (data) => {
  if (data.new_password !== data.new_password_confirm) {
    passwordForm.querySelector('[data-error-for="new_password_confirm"]').textContent =
      "パスワードが一致しません";
    return;
  }
  await authApi.changePassword(data.current_password, data.new_password);
  await startProfileStep();
});

// ───────── ② プロフィール ─────────

let masterData;
let profileFields;

async function startProfileStep() {
  masterData = await masterDataApi.loadAll();
  const form = document.getElementById("profile-form");
  profileFields = renderProfileFields(form.querySelector("[data-fields]"), masterData, null);
  showStep("profile");
}

handleSubmit(document.getElementById("profile-form"), async () => {
  const values = profileFields.getValues();
  if (!values) return;
  let profile = await profileApi.save(values);
  if (values.avatarFile) {
    try {
      profile = await profileApi.uploadAvatar(values.avatarFile);
    } catch (err) {
      // 画像だけ失敗しても、プロフィールの登録は済んでいるので先に進める
      showToast(`画像を登録できませんでした（${err.message}）。マイプロフィールから再度登録できます`, "error");
    }
  }
  if (profile.is_engineer) startSkillsStep();
  else showStep("seat");
});

// ───────── ③ 技術スキル ─────────

let skillsEditor;

function startSkillsStep() {
  const form = document.getElementById("skills-form");
  skillsEditor = renderSkillsEditor(form.querySelector("[data-skills]"), masterData.skills, []);
  showStep("skills");
}

const skillsForm = document.getElementById("skills-form");
handleSubmit(skillsForm, async () => {
  let skills;
  try {
    skills = skillsEditor.getValue();
  } catch (err) {
    showFormError(skillsForm, err.message);
    return;
  }
  await profileApi.saveSkills(skills);
  showStep("seat");
});

// ───────── 開始 ─────────

if (me.must_change_password) showStep("password");
else await startProfileStep();
