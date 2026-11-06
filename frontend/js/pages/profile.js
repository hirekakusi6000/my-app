import { authApi } from "../api/auth.js";
import { masterDataApi } from "../api/master-data.js";
import { profileApi } from "../api/profile.js";
import { renderHeader } from "../components/app-header.js";
import { renderProfileFields } from "../components/profile-fields.js";
import { renderSkillsEditor } from "../components/skills-editor.js";
import { requireAuth } from "../lib/auth-guard.js";
import { handleSubmit, showFormError } from "../lib/form.js";
import { showToast } from "../lib/toast.js";

const me = await requireAuth({ role: "general" });
renderHeader(document.getElementById("app-header"), me);

let [masterData, profile] = await Promise.all([masterDataApi.loadAll(), profileApi.getMine()]);

const profileForm = document.getElementById("profile-form");
const skillsPanel = document.getElementById("skills-panel");
const skillsForm = document.getElementById("skills-form");
let profileFields;
let skillsEditor;

function render() {
  profileFields = renderProfileFields(profileForm.querySelector("[data-fields]"), masterData, profile, {
    allowAvatarDelete: true,
  });
  // 技術スキルの欄は、保存済みの職種がエンジニアの場合に表示する
  skillsPanel.hidden = !profile.is_engineer;
  if (profile.is_engineer) {
    skillsEditor = renderSkillsEditor(skillsForm.querySelector("[data-skills]"), masterData.skills, profile.skills);
  }
}

render();

handleSubmit(profileForm, async () => {
  const values = profileFields.getValues();
  if (!values) return;
  profile = await profileApi.save({ ...values, defaultSeatId: profile.default_seat_id });
  if (values.avatarFile) profile = await profileApi.uploadAvatar(values.avatarFile);
  else if (values.deleteAvatar) {
    await profileApi.deleteAvatar();
    profile = await profileApi.getMine();
  }
  // 新しい役職・職種が候補に追加されている可能性があるので読み直す
  masterData = await masterDataApi.loadAll();
  render();
  showToast("プロフィールを保存しました");
});

handleSubmit(skillsForm, async () => {
  let skills;
  try {
    skills = skillsEditor.getValue();
  } catch (err) {
    showFormError(skillsForm, err.message);
    return;
  }
  await profileApi.saveSkills(skills);
  [masterData, profile] = await Promise.all([masterDataApi.loadAll(), profileApi.getMine()]);
  render();
  showToast("技術スキルを保存しました");
});

const passwordForm = document.getElementById("password-form");
handleSubmit(passwordForm, async (data) => {
  if (data.new_password !== data.new_password_confirm) {
    passwordForm.querySelector('[data-error-for="new_password_confirm"]').textContent =
      "パスワードが一致しません";
    return;
  }
  await authApi.changePassword(data.current_password, data.new_password);
  passwordForm.reset();
  showToast("パスワードを変更しました");
});
