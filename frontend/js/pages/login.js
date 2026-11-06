import { authApi } from "../api/auth.js";
import { homePathFor, redirectIfLoggedIn } from "../lib/auth-guard.js";
import { handleSubmit } from "../lib/form.js";

await redirectIfLoggedIn();

handleSubmit(document.getElementById("login-form"), async ({ email, password }) => {
  const me = await authApi.login(email.trim(), password);
  window.location.replace(homePathFor(me));
});
