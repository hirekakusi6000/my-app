import { officesApi } from "../api/offices.js";
import { renderHeader } from "../components/app-header.js";
import { CELL, createRoomSvg, drawFurniture, drawOccupants } from "../components/map-renderer.js";
import { openProfilePopup } from "../components/profile-popup.js";
import { requireAuth } from "../lib/auth-guard.js";

const POLL_INTERVAL_MS = 30_000;
const LAST_ROOM_KEY = "map:lastRoomId";

const me = await requireAuth();
renderHeader(document.getElementById("app-header"), me);

const nav = document.getElementById("room-nav");
const stage = document.getElementById("stage");
const titleEl = document.getElementById("room-title");
const updatedEl = document.getElementById("updated");

let current = null; // { room, seats: Map, svgParts }
let pollTimer = null;

// ───────── 部屋の一覧 ─────────

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
  } else {
    const hint = document.createElement("p");
    hint.className = "field__hint";
    hint.textContent = "管理者がマップを作成すると、ここに表示されます。";
    empty.append(hint);
  }
  stage.append(empty);
} else {
  let saved = null;
  try {
    saved = Number(localStorage.getItem(LAST_ROOM_KEY));
  } catch {
    // 保存できない環境でも動くようにする
  }
  await showRoom(rooms.some((r) => r.id === saved) ? saved : rooms[0].id);
}

// ───────── 部屋の表示 ─────────

async function showRoom(roomId) {
  const layout = await officesApi.getLayout(roomId);
  const room = layout.room;
  try {
    localStorage.setItem(LAST_ROOM_KEY, String(roomId));
  } catch {
    // 無視
  }
  renderNav(roomId);
  titleEl.textContent = `${layout.floor_name} / ${room.name}`;

  const svgParts = createRoomSvg(room);
  svgParts.svg.style.width = `${room.width * CELL}px`;
  for (const item of layout.furniture) svgParts.furnitureLayer.append(drawFurniture(item));
  stage.replaceChildren(svgParts.svg);

  const seats = new Map(layout.furniture.filter((f) => f.type === "chair").map((f) => [f.id, f]));
  current = { room, seats, svgParts };
  await refreshOccupants();

  clearInterval(pollTimer);
  pollTimer = setInterval(refreshOccupants, POLL_INTERVAL_MS);
}

async function refreshOccupants() {
  if (!current || document.hidden) return;
  const roomId = current.room.id;
  try {
    const occupants = await officesApi.getOccupancy(roomId);
    if (current.room.id !== roomId) return; // 取得中に部屋が切り替わった
    drawOccupants(current.svgParts.overlayLayer, current.seats, occupants, (o) =>
      openProfilePopup(o.user_id),
    );
    updatedEl.textContent = `${new Date().toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" })} 時点`;
  } catch (err) {
    updatedEl.textContent = `更新できませんでした（${err.message}）`;
  }
}

// タブを開き直したときは、すぐに最新の状態にする
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) refreshOccupants();
});
