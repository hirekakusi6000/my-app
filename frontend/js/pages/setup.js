import { authApi } from "../api/auth.js";
import { renderHeader } from "../components/app-header.js";
import { requireAuth } from "../lib/auth-guard.js";
import { handleSubmit } from "../lib/form.js";

const me = await requireAuth({ role: "general", setupPage: true });
renderHeader(document.getElementById("app-header"), me, { nav: false });

function showStep(step) {
  document.querySelectorAll(".steps li").forEach((li) => {
    if (li.dataset.step === step) li.setAttribute("aria-current", "step");
    else li.removeAttribute("aria-current");
  });
  document.getElementById("step-password").hidden = step !== "password";
  document.getElementById("step-profile").hidden = step !== "profile";
}

showStep(me.must_change_password ? "password" : "profile");

const form = document.getElementById("password-form");
handleSubmit(form, async (data) => {
  if (data.new_password !== data.new_password_confirm) {
    form.querySelector('[data-error-for="new_password_confirm"]').textContent =
      "パスワードが一致しません";
    return;
  }
  await authApi.changePassword(data.current_password, data.new_password);
  showStep("profile");
});
