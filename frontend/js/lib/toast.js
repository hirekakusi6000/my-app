// 画面右上に一時的に表示するお知らせ。

let container;

function ensureContainer() {
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    container.setAttribute("role", "status");
    container.setAttribute("aria-live", "polite");
    document.body.append(container);
  }
  return container;
}

/**
 * @param {string} message
 * @param {"success" | "error"} type
 */
export function showToast(message, type = "success") {
  const el = document.createElement("div");
  el.className = `toast toast--${type}`;
  el.textContent = message;
  ensureContainer().append(el);
  setTimeout(() => el.remove(), 4000);
}
