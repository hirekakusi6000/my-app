import { authApi } from "../api/auth.js";
import { homePathFor, redirectIfLoggedIn } from "../lib/auth-guard.js";
import { handleSubmit } from "../lib/form.js";

await redirectIfLoggedIn();

const form = document.getElementById("signup-form");

handleSubmit(form, async (data) => {
  if (data.password !== data.password_confirm) {
    form.querySelector('[data-error-for="password_confirm"]').textContent =
      "パスワードが一致しません";
    return;
  }
  const me = await authApi.signup(data.organization_name.trim(), data.email.trim(), data.password);
  window.location.replace(homePathFor(me));
});
