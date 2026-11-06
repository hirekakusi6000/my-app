import { fetchHello } from "./api.js";

async function init() {
  const el = document.getElementById("message");
  try {
    const data = await fetchHello();
    el.textContent = data.message;
  } catch (err) {
    el.textContent = "Failed to load message";
    console.error(err);
  }
}

init();
