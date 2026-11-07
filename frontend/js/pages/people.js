import { masterDataApi } from "../api/master-data.js";
import { peopleApi } from "../api/people.js";
import { renderHeader } from "../components/app-header.js";
import { STATUS_LABELS, staleLabel } from "../components/map-renderer.js";
import { openProfilePopup } from "../components/profile-popup.js";
import { requireAuth } from "../lib/auth-guard.js";
import { showToast } from "../lib/toast.js";

const MAX_SKILLS = 5;

const me = await requireAuth();
renderHeader(document.getElementById("app-header"), me);

const form = document.getElementById("search-form");
const skillInput = document.getElementById("skill-input");
const chipsEl = document.getElementById("skill-chips");
const resultsEl = document.getElementById("results");
const countEl = document.getElementById("result-count");

/** 検索条件に入れたスキル名 */
let skills = [];

// スキルの候補（入力欄の候補として表示する）
const allSkills = await masterDataApi.loadAll().then((d) => d.skills).catch(() => []);
document.getElementById("skill-options").replaceChildren(
  ...[...new Set(allSkills.map((s) => s.name))].map((name) => new Option(name)),
);

// ───────── 条件 ─────────

function addSkill() {
  const name = skillInput.value.trim();
  skillInput.value = "";
  if (!name) return;
  if (skills.some((s) => s.toLowerCase() === name.toLowerCase())) return;
  if (skills.length >= MAX_SKILLS) {
    showToast(`スキルは${MAX_SKILLS}つまで指定できます`, "error");
    return;
  }
  skills.push(name);
  renderChips();
  search();
}

function renderChips() {
  chipsEl.replaceChildren(
    ...skills.map((name) => {
      const chip = document.createElement("span");
      chip.className = "chip chip--removable";
      chip.textContent = name;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.setAttribute("aria-label", `${name} を条件から外す`);
      remove.textContent = "×";
      remove.addEventListener("click", () => {
        skills = skills.filter((s) => s !== name);
        renderChips();
        search();
      });
      chip.append(remove);
      return chip;
    }),
  );
}

document.getElementById("add-skill").addEventListener("click", addSkill);
skillInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    addSkill();
  }
});
// 候補の一覧から選んだときもすぐに追加する
skillInput.addEventListener("change", () => {
  if (allSkills.some((s) => s.name === skillInput.value.trim())) addSkill();
});

form.addEventListener("submit", (e) => e.preventDefault());
form.addEventListener("change", (e) => {
  if (e.target !== skillInput) search();
});
let typingTimer;
form.elements.name.addEventListener("input", () => {
  clearTimeout(typingTimer);
  typingTimer = setTimeout(search, 300); // 入力が止まってから検索する
});

// ───────── 検索・表示 ─────────

let latestRequest = 0;

async function search() {
  const requestId = ++latestRequest;
  const query = {
    name: form.elements.name.value,
    skills,
    minYears: Number(form.elements.min_years.value),
    statuses: [...form.querySelectorAll('[name="status"]:checked')].map((c) => c.value),
  };
  try {
    const people = await peopleApi.search(query);
    if (requestId !== latestRequest) return; // 古い検索の結果は捨てる
    render(people, query);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function el(tag, className, text) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text !== undefined) e.textContent = text;
  return e;
}

function render(people, query) {
  countEl.textContent = `${people.length}人`;
  resultsEl.replaceChildren();
  if (!people.length) {
    resultsEl.append(el("p", "empty-state", "条件に合うメンバーはいません"));
    return;
  }
  const wanted = new Set(query.skills.map((s) => s.toLowerCase()));

  for (const p of people) {
    const card = el("article", "person-card");

    const head = el("button", "person-card__head");
    head.type = "button";
    head.addEventListener("click", () => openProfilePopup(p.user_id));
    if (p.avatar_url) {
      const img = el("img", "avatar avatar--md");
      img.src = p.avatar_url;
      img.alt = "";
      head.append(img);
    } else {
      head.append(el("span", "avatar avatar--md avatar--placeholder", p.name.charAt(0)));
    }
    const who = el("span", "person-card__who");
    who.append(
      el("strong", "", p.name),
      el("span", "person-card__meta", [p.position, p.job_type].filter(Boolean).join(" ・ ")),
    );
    head.append(who);
    card.append(head);

    const statusRow = el("div", "person-card__status");
    statusRow.append(el("span", `status-badge status-badge--${p.status}`, STATUS_LABELS[p.status]));
    if (p.is_stale) {
      const tag = el("span", "stale-tag", "前日から");
      tag.title = staleLabel(p.updated_at);
      statusRow.append(tag);
    }
    if (p.seat) {
      const seatText = `${p.seat.floor_name} / ${p.seat.room_name}${p.seat.label ? ` / ${p.seat.label}` : ""}`;
      const link = el("a", "person-card__seat", `${seatText}（マップで見る）`);
      link.href = `/map.html?room=${p.seat.room_id}&seat=${p.seat.seat_id}`;
      statusRow.append(link);
    }
    card.append(statusRow);
    if (p.comment) card.append(el("p", "person-card__comment", `💬 ${p.comment}`));

    if (p.skills.length) {
      const chips = el("div", "chips");
      for (const s of p.skills) {
        // 検索条件のスキルは目立たせる
        const matched = wanted.has(s.name.toLowerCase());
        chips.append(el("span", `chip${matched ? " chip--matched" : ""}`, `${s.name} ${s.years}年`));
      }
      card.append(chips);
    }
    resultsEl.append(card);
  }
}

await search();
