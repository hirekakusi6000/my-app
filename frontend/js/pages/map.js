import { officesApi } from "../api/offices.js";
import { presenceApi } from "../api/presence.js";
import { profileApi } from "../api/profile.js";
import { renderHeader } from "../components/app-header.js";
import {
  CELL,
  createRoomSvg,
  drawFurniture,
  drawOccupants,
  STATUS_LABELS,
  staleLabel,
} from "../components/map-renderer.js";
import { openProfilePopup } from "../components/profile-popup.js";
import { renderSampleDataBanner } from "../components/sample-data-banner.js";
import { requireAuth } from "../lib/auth-guard.js";
import { showToast } from "../lib/toast.js";

const POLL_INTERVAL_MS = 30_000;
const LAST_ROOM_KEY = "map:lastRoomId";

const me = await requireAuth();
renderHeader(document.getElementById("app-header"), me);
const isGeneral = me.role === "general";

const nav = document.getElementById("room-nav");
const stage = document.getElementById("stage");
const titleEl = document.getElementById("room-title");
const updatedEl = document.getElementById("updated");
const pickBar = document.getElementById("pick-bar");
const pickText = document.getElementById("pick-text");
const pickOk = document.getElementById("pick-ok");

// ───────── 状態 ─────────

let current = null; // 表示中の部屋 { room, seats: Map<id, 家具>, svgParts, occupants }
let myPresence = null; // 自分の勤務状況（一般ユーザーのみ）
let defaultSeat = null; // デフォルト座席の場所（一般ユーザーのみ）
let picking = null; // 座席の選択中 { seatId: number | null }
let pollTimer = null;

function seatLabel(seat) {
  if (!seat) return "";
  return `${seat.floor_name} / ${seat.room_name}${seat.label ? ` / ${seat.label}` : ""}`;
}

// ───────── 部屋の一覧と表示 ─────────

const floors = await officesApi.listFloors();
const rooms = floors.flatMap((f) => f.rooms.map((r) => ({ ...r, floorName: f.name })));

function renderNav(activeId) {
  nav.replaceChildren();
  for (const f of floors) {
    const floorItem = document.createElement("li");
    floorItem.className = "room-nav__floor";
    floorItem.textContent = f.name;
    nav.append(floorItem);
    for (const r of f.rooms) {
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.type = "button";
      b.className = "room-nav__room";
      b.textContent = r.name;
      b.setAttribute("aria-current", String(r.id === activeId));
      b.addEventListener("click", () => showRoom(r.id));
      li.append(b);
      nav.append(li);
    }
  }
}

async function showRoom(roomId) {
  const layout = await officesApi.getLayout(roomId);
  const room = layout.room;
  try {
    localStorage.setItem(LAST_ROOM_KEY, String(roomId));
  } catch {
    // 保存できない環境でも動くようにする
  }
  renderNav(roomId);
  titleEl.textContent = `${layout.floor_name} / ${room.name}`;

  const svgParts = createRoomSvg(room);
  svgParts.svg.style.width = `${room.width * CELL}px`;
  for (const item of layout.furniture) {
    const g = drawFurniture(item);
    if (item.type === "chair") {
      g.dataset.seatId = item.id;
      g.addEventListener("click", () => onSeatClick(item.id));
    }
    svgParts.furnitureLayer.append(g);
  }
  stage.replaceChildren(svgParts.svg);

  const seats = new Map(layout.furniture.filter((f) => f.type === "chair").map((f) => [f.id, f]));
  current = { room, seats, svgParts, occupants: [] };
  await refreshOccupants();
}

async function refreshOccupants() {
  if (!current) return;
  const roomId = current.room.id;
  const occupants = await officesApi.getOccupancy(roomId);
  if (current.room.id !== roomId) return; // 取得中に部屋が切り替わった
  current.occupants = occupants;
  drawOccupants(current.svgParts.overlayLayer, current.seats, occupants, onOccupantClick);
  decorateSeats();
}

/** 座席の選択中は、空いている椅子・使用中の椅子・選んだ椅子を見分けられるようにする */
function decorateSeats() {
  if (!current) return;
  const svg = current.svgParts.svg;
  svg.classList.toggle("room-map--pickable", Boolean(picking));
  // 選択中はアイコンをクリックできないようにし、椅子を選びやすくする
  current.svgParts.overlayLayer.style.pointerEvents = picking ? "none" : "";
  const taken = new Set(
    current.occupants.filter((o) => o.user_id !== myPresence?.user_id).map((o) => o.seat_id),
  );
  svg.querySelectorAll("[data-seat-id]").forEach((g) => {
    const id = Number(g.dataset.seatId);
    g.classList.toggle("furniture--taken", Boolean(picking) && taken.has(id));
    g.classList.toggle("furniture--picked", Boolean(picking) && picking.seatId === id);
    g.classList.toggle(
      "furniture--highlight",
      Boolean(picking) && defaultSeat?.seat_id === id && picking.seatId !== id,
    );
  });
  if (picking) updatePickBar();
}

// ───────── 自分の状態（一般ユーザー） ─────────

const ACTIONS = {
  not_working: [
    ["出社", () => startPicking()],
    ["リモート", () => changeStatus("remote")],
  ],
  present: [
    ["離席", () => changeStatus("away")],
    ["座席変更", () => startPicking()],
    ["退勤", () => changeStatus("not_working")],
  ],
  away: [
    ["在席に戻る", () => changeStatus("present", myPresence.seat.seat_id)],
    ["座席変更", () => startPicking()],
    ["退勤", () => changeStatus("not_working")],
  ],
  remote: [
    ["出社", () => startPicking()],
    ["退勤", () => changeStatus("not_working")],
  ],
};

function renderMyStatus() {
  if (!myPresence) return;
  const badge = document.getElementById("my-badge");
  badge.className = `status-badge status-badge--${myPresence.status}`;
  badge.textContent = STATUS_LABELS[myPresence.status];
  document.getElementById("my-seat").textContent = myPresence.seat ? seatLabel(myPresence.seat) : "";
  // 前日の状態のままなら、今日の状態に更新するよう案内する
  document.getElementById("my-stale").hidden = !myPresence.is_stale;

  const actions = document.getElementById("my-actions");
  actions.replaceChildren();
  for (const [label, handler] of ACTIONS[myPresence.status]) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = label === "退勤" ? "button button--ghost" : "button";
    b.textContent = label;
    b.disabled = Boolean(picking);
    b.addEventListener("click", handler);
    actions.append(b);
  }
  const commentInput = document.querySelector('#comment-form [name="comment"]');
  if (document.activeElement !== commentInput) commentInput.value = myPresence.comment ?? "";
}

async function changeStatus(status, seatId = null, { comment } = {}) {
  try {
    myPresence = await presenceApi.update(status, { seatId, comment });
    renderMyStatus();
    await refreshAll();
    return true;
  } catch (err) {
    showToast(err.message, "error");
    if (err.code === "SEAT_OCCUPIED") await refreshAll();
    return false;
  }
}

document.getElementById("comment-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const comment = e.currentTarget.elements.comment.value.trim();
  const seatId = myPresence.seat?.seat_id ?? null;
  if (await changeStatus(myPresence.status, seatId, { comment: comment || null })) {
    showToast("コメントを保存しました");
  }
});

// ───────── 座席の選択（出社・座席変更） ─────────

async function startPicking() {
  if (rooms.length === 0) {
    showToast("オフィスマップがまだ作成されていません", "error");
    return;
  }
  const isChange = myPresence.status === "present" || myPresence.status === "away";
  picking = { seatId: null };
  pickOk.textContent = isChange ? "この座席に移動" : "この座席で出社";

  // 出社のときは、空いていればデフォルト座席を最初から選んでおく
  if (!isChange && defaultSeat) {
    if (current?.room.id !== defaultSeat.room_id) await showRoom(defaultSeat.room_id);
    const takenByOthers = current.occupants.some(
      (o) => o.seat_id === defaultSeat.seat_id && o.user_id !== myPresence.user_id,
    );
    if (!takenByOthers) picking.seatId = defaultSeat.seat_id;
  }
  pickBar.hidden = false;
  updatePickBar();
  decorateSeats();
  renderMyStatus();
}

function stopPicking() {
  picking = null;
  pickBar.hidden = true;
  decorateSeats();
  renderMyStatus();
}

function updatePickBar() {
  const seat = picking?.seatId ? current?.seats.get(picking.seatId) : null;
  pickOk.disabled = !picking?.seatId;
  if (picking?.seatId && seat) {
    pickText.textContent = `選択中：${titleEl.textContent}${seat.label ? ` / ${seat.label}` : ""}`;
  } else if (picking?.seatId) {
    pickText.textContent = "選択中の座席は別の部屋にあります";
  } else {
    pickText.textContent = "空いている椅子をクリックして選んでください";
  }
}

function onSeatClick(seatId) {
  if (!picking) return;
  const takenByOthers = current.occupants.some(
    (o) => o.seat_id === seatId && o.user_id !== myPresence.user_id,
  );
  if (takenByOthers) {
    showToast("この座席は使用中です", "error");
    return;
  }
  picking.seatId = seatId;
  updatePickBar();
  decorateSeats();
}

document.getElementById("pick-cancel").addEventListener("click", stopPicking);
pickOk.addEventListener("click", async () => {
  const seatId = picking?.seatId;
  if (!seatId) return;
  pickOk.disabled = true;
  if (await changeStatus("present", seatId)) {
    stopPicking();
    showToast("出社しました");
  } else {
    picking.seatId = null;
    updatePickBar();
    decorateSeats();
  }
});

// ───────── アイコンのクリック ─────────

function onOccupantClick(occupant) {
  const actions = [];
  if (me.role === "master") {
    actions.push({
      label: "座席を空ける",
      danger: true,
      onClick: async () => {
        if (!confirm(`${occupant.name ?? "この人"}の座席を空けますか？\nこの人は「未出勤」になります。`)) return false;
        try {
          await presenceApi.releaseSeat(occupant.seat_id);
          showToast("座席を空けました");
          await refreshAll();
          return true;
        } catch (err) {
          showToast(err.message, "error");
          return false;
        }
      },
    });
  }
  openProfilePopup(occupant.user_id, { actions });
}

// ───────── リモートの一覧 ─────────

function renderRemoteList(entries) {
  const remote = entries.filter((e) => e.status === "remote");
  document.getElementById("remote-count").textContent = `(${remote.length})`;
  const list = document.getElementById("remote-list");
  list.replaceChildren();
  if (!remote.length) {
    const li = document.createElement("li");
    li.className = "people-list__empty";
    li.textContent = "いません";
    list.append(li);
    return;
  }
  for (const e of remote) {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.type = "button";
    b.className = "people-list__person";
    const name = document.createElement("span");
    name.className = "people-list__name";
    name.textContent = e.name ?? "名前未登録";
    b.append(name);
    if (e.is_stale) {
      const stale = document.createElement("span");
      stale.className = "stale-tag";
      stale.textContent = "前日から";
      stale.title = staleLabel(e.updated_at);
      name.append(" ", stale);
    }
    if (e.comment) {
      const comment = document.createElement("span");
      comment.className = "people-list__comment";
      comment.textContent = e.comment;
      b.append(comment);
    }
    b.addEventListener("click", () => openProfilePopup(e.user_id));
    li.append(b);
    list.append(li);
  }
}

// ───────── 更新 ─────────

async function refreshAll() {
  try {
    const [entries] = await Promise.all([presenceApi.list(), refreshOccupants()]);
    renderRemoteList(entries);
    if (isGeneral) {
      myPresence = entries.find((e) => e.user_id === myPresence?.user_id) ?? myPresence;
      renderMyStatus();
    }
    updatedEl.textContent = `${new Date().toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" })} 時点`;
  } catch (err) {
    updatedEl.textContent = `更新できませんでした（${err.message}）`;
  }
}

// ───────── 開始 ─────────

if (isGeneral) {
  const [presence, profile] = await Promise.all([presenceApi.getMine(), profileApi.getMine()]);
  myPresence = presence;
  defaultSeat = profile.default_seat;
  document.getElementById("my-status").hidden = false;
  renderMyStatus();
}

if (rooms.length === 0) {
  titleEl.textContent = "マップ";
  const empty = document.createElement("div");
  empty.className = "empty-state";
  const message = document.createElement("p");
  message.textContent = "まだオフィスマップがありません。";
  empty.append(message);
  if (me.role === "master") {
    const link = document.createElement("a");
    link.className = "button";
    link.href = "/admin/offices.html";
    link.textContent = "フロア・部屋を作成する";
    empty.append(link);
    // サンプルデータを作成できる場合は、そのボタンも出す
    const banner = document.createElement("div");
    banner.hidden = true;
    empty.append(banner);
    renderSampleDataBanner(banner, { onCreated: () => window.location.reload() });
  } else {
    const hint = document.createElement("p");
    hint.className = "field__hint";
    hint.textContent = "管理者がマップを作成すると、ここに表示されます。リモートの登録はできます。";
    empty.append(hint);
  }
  stage.append(empty);
  renderRemoteList(await presenceApi.list());
} else {
  let saved = null;
  try {
    saved = Number(localStorage.getItem(LAST_ROOM_KEY));
  } catch {
    // 無視
  }
  // 開く部屋の優先順：URL で指定された部屋（メンバー画面の「マップで見る」）→
  // 出社中なら自分の座席がある部屋 → 前回の部屋
  const params = new URLSearchParams(window.location.search);
  const requested = Number(params.get("room"));
  const mine = myPresence?.seat?.room_id;
  const initial =
    [requested, mine, saved].find((id) => rooms.some((r) => r.id === id)) ?? rooms[0].id;
  await showRoom(initial);
  await refreshAll();
  if (requested === initial && params.get("seat")) focusSeat(Number(params.get("seat")));
}

/** 指定した座席に座っている人を目立たせ、画面内に表示する */
function focusSeat(seatId) {
  const icon = current?.svgParts.overlayLayer.querySelector(`[data-seat-id="${seatId}"]`);
  if (!icon) {
    showToast("その座席には今は誰も座っていません", "error");
    return;
  }
  icon.classList.add("occupant--focus");
  icon.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });
  setTimeout(() => icon.classList.remove("occupant--focus"), 4000);
}

pollTimer = setInterval(() => {
  if (!document.hidden) refreshAll();
}, POLL_INTERVAL_MS);

// タブを開き直したときは、すぐに最新の状態にする
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) refreshAll();
});
