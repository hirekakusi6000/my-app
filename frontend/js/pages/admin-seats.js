import { presenceApi } from "../api/presence.js";
import { renderHeader } from "../components/app-header.js";
import { STATUS_LABELS } from "../components/map-renderer.js";
import { requireAuth } from "../lib/auth-guard.js";
import { showToast } from "../lib/toast.js";

const me = await requireAuth({ role: "master" });
renderHeader(document.getElementById("app-header"), me);

const rowsEl = document.getElementById("rows");
const summaryEl = document.getElementById("summary");

function cell(text, className = "") {
  const td = document.createElement("td");
  td.className = className;
  td.textContent = text;
  return td;
}

function formatDateTime(iso) {
  return new Date(iso).toLocaleString("ja-JP", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderSummary(entries) {
  const counts = { present: 0, away: 0, remote: 0, not_working: 0 };
  for (const e of entries) counts[e.status] += 1;
  summaryEl.replaceChildren(
    ...Object.entries(counts).map(([status, n]) => {
      const item = document.createElement("div");
      item.className = "summary__item";
      const badge = document.createElement("span");
      badge.className = `status-badge status-badge--${status}`;
      badge.textContent = STATUS_LABELS[status];
      const count = document.createElement("strong");
      count.textContent = `${n}名`;
      item.append(badge, count);
      return item;
    }),
  );
}

function renderStaleBanner(entries) {
  const stale = entries.filter((e) => e.is_stale);
  const banner = document.getElementById("stale-banner");
  banner.hidden = stale.length === 0;
  const seated = stale.filter((e) => e.seat).length;
  document.getElementById("stale-text").textContent =
    `前日から状態を更新していない人が ${stale.length}名 います（うち座席を使用中 ${seated}名）。` +
    "退勤し忘れの可能性があります。";
}

document.getElementById("reset-stale").addEventListener("click", async () => {
  if (!confirm("前日から状態を更新していない人を、まとめて「未出勤」に戻しますか？\n座っていた座席は空きます。")) return;
  try {
    const { count } = await presenceApi.resetStale();
    showToast(`${count}名を未出勤に戻しました`);
  } catch (err) {
    showToast(err.message, "error");
  }
  await reload();
});

function updatedCell(e) {
  const td = cell(formatDateTime(e.updated_at));
  if (e.is_stale) {
    const tag = document.createElement("span");
    tag.className = "stale-tag";
    tag.textContent = "前日から";
    td.append(" ", tag);
  }
  return td;
}

async function reload() {
  const entries = await presenceApi.list();
  renderSummary(entries);
  renderStaleBanner(entries);
  const seated = entries.filter((e) => e.seat);
  rowsEl.replaceChildren();
  if (!seated.length) {
    const tr = document.createElement("tr");
    tr.append(cell("使用中の座席はありません", "table__empty"));
    tr.firstChild.colSpan = 6;
    rowsEl.append(tr);
    return;
  }
  for (const e of seated) {
    const tr = document.createElement("tr");
    const statusTd = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `status-badge status-badge--${e.status}`;
    badge.textContent = STATUS_LABELS[e.status];
    statusTd.append(badge);

    const seat = `${e.seat.floor_name} / ${e.seat.room_name}${e.seat.label ? ` / ${e.seat.label}` : ""}`;
    const actions = document.createElement("td");
    actions.className = "table__actions";
    const b = document.createElement("button");
    b.type = "button";
    b.className = "button button--ghost button--small button--danger-text";
    b.textContent = "座席を空ける";
    b.addEventListener("click", async () => {
      if (!confirm(`${e.name ?? "この人"}の座席（${seat}）を空けますか？\nこの人は「未出勤」になります。`)) return;
      try {
        await presenceApi.releaseSeat(e.seat.seat_id);
        showToast("座席を空けました");
      } catch (err) {
        showToast(err.message, "error");
      }
      await reload();
    });
    actions.append(b);

    tr.append(
      cell(e.name ?? "名前未登録"),
      statusTd,
      cell(seat),
      cell(e.comment ?? "—", e.comment ? "" : "table__muted"),
      updatedCell(e),
      actions,
    );
    rowsEl.append(tr);
  }
}

document.getElementById("reload").addEventListener("click", async () => {
  await reload();
  showToast("最新の状態にしました");
});

await reload();
