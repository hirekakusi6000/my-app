import { officesApi } from "../api/offices.js";
import { renderHeader } from "../components/app-header.js";
import { requireAuth } from "../lib/auth-guard.js";
import { clearErrors, handleSubmit } from "../lib/form.js";
import { showToast } from "../lib/toast.js";

const MAX_FLOORS = 5;
const MAX_ROOMS = 5;

const me = await requireAuth({ role: "master" });
renderHeader(document.getElementById("app-header"), me);

const floorsEl = document.getElementById("floors");
const floorDialog = document.getElementById("floor-dialog");
const roomDialog = document.getElementById("room-dialog");
const floorForm = document.getElementById("floor-form");
const roomForm = document.getElementById("room-form");

let floors = [];
/** ダイアログで編集中の対象 */
let editing = null;

for (const d of [floorDialog, roomDialog]) {
  d.querySelector("[data-close]").addEventListener("click", () => d.close());
}

function el(tag, className, text) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text !== undefined) e.textContent = text;
  return e;
}

function button(label, onClick, extra = "") {
  const b = el("button", `button button--ghost button--small ${extra}`, label);
  b.type = "button";
  b.addEventListener("click", onClick);
  return b;
}

// ───────── 表示 ─────────

function render() {
  floorsEl.replaceChildren();
  document.getElementById("floor-count").textContent = `（${floors.length} / ${MAX_FLOORS}）`;
  document.getElementById("add-floor").disabled = floors.length >= MAX_FLOORS;

  if (floors.length === 0) {
    const empty = el("section", "panel empty-state");
    empty.append(
      el("p", "", "まだフロアがありません。"),
      el("p", "field__hint", "「＋ フロアを追加」から始めましょう（例：1F）。"),
    );
    floorsEl.append(empty);
    return;
  }

  floors.forEach((floor, index) => {
    const panel = el("section", "panel");
    const head = el("div", "panel__head");
    const title = el("h2", "panel__title", floor.name);
    const actions = el("div", "panel__head-actions");
    const up = button("↑", () => swapFloors(index, index - 1));
    up.disabled = index === 0;
    up.title = "上へ";
    const down = button("↓", () => swapFloors(index, index + 1));
    down.disabled = index === floors.length - 1;
    down.title = "下へ";
    const addRoom = button("＋ 部屋を追加", () => openRoomDialog(floor, null));
    addRoom.disabled = floor.rooms.length >= MAX_ROOMS;
    actions.append(
      up,
      down,
      button("名前変更", () => openFloorDialog(floor)),
      addRoom,
      button("削除", () => removeFloor(floor), "button--danger-text"),
    );
    head.append(title, actions);
    panel.append(head);

    if (floor.rooms.length === 0) {
      panel.append(el("p", "field__hint", "部屋がありません。"));
    } else {
      const list = el("ul", "item-list");
      for (const room of floor.rooms) {
        const li = el("li", "item-list__item");
        li.append(
          el("span", "item-list__name", room.name),
          el("span", "badge badge--muted", `${room.width} × ${room.height} マス`),
        );
        const roomActions = el("span", "item-list__actions");
        const editLink = el("a", "button button--small", "配置を編集");
        editLink.href = `/admin/map-editor.html?room=${room.id}`;
        roomActions.append(
          editLink,
          button("設定", () => openRoomDialog(floor, room)),
          button("削除", () => removeRoom(room), "button--danger-text"),
        );
        li.append(roomActions);
        list.append(li);
      }
      panel.append(list);
    }
    floorsEl.append(panel);
  });
}

async function reload() {
  floors = await officesApi.listFloors();
  render();
}

// ───────── フロア ─────────

document.getElementById("add-floor").addEventListener("click", () => openFloorDialog(null));

function openFloorDialog(floor) {
  editing = floor;
  floorForm.reset();
  clearErrors(floorForm);
  floorDialog.querySelector("[data-title]").textContent = floor ? "フロア名の変更" : "フロアを追加";
  if (floor) floorForm.elements.name.value = floor.name;
  floorDialog.showModal();
}

handleSubmit(floorForm, async ({ name }) => {
  if (editing) await officesApi.updateFloor(editing.id, { name: name.trim() });
  else await officesApi.createFloor(name.trim());
  floorDialog.close();
  await reload();
  showToast(editing ? "フロア名を変更しました" : "フロアを追加しました");
});

async function swapFloors(a, b) {
  const fa = floors[a];
  const fb = floors[b];
  try {
    // 並び順の値を入れ替える（同じ値の場合も考えて、位置の番号を使う）
    await officesApi.updateFloor(fa.id, { sort_order: b });
    await officesApi.updateFloor(fb.id, { sort_order: a });
    await reload();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function removeFloor(floor) {
  const roomNote = floor.rooms.length ? `\n中にある部屋（${floor.rooms.length}室）と家具もすべて削除されます。` : "";
  if (!confirm(`「${floor.name}」を削除しますか？${roomNote}\n座っている人は「未出勤」に戻ります。`)) return;
  try {
    await officesApi.deleteFloor(floor.id);
    await reload();
    showToast("フロアを削除しました");
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ───────── 部屋 ─────────

let roomFloor = null;

function openRoomDialog(floor, room) {
  roomFloor = floor;
  editing = room;
  roomForm.reset();
  clearErrors(roomForm);
  roomDialog.querySelector("[data-title]").textContent = room ? "部屋の設定" : `部屋を追加（${floor.name}）`;
  if (room) {
    roomForm.elements.name.value = room.name;
    roomForm.elements.width.value = room.width;
    roomForm.elements.height.value = room.height;
  }
  roomDialog.showModal();
}

handleSubmit(roomForm, async ({ name, width, height }) => {
  const fields = { name: name.trim(), width: Number(width), height: Number(height) };
  if (editing) await officesApi.updateRoom(editing.id, fields);
  else await officesApi.createRoom(roomFloor.id, fields);
  roomDialog.close();
  await reload();
  showToast(editing ? "部屋の設定を変更しました" : "部屋を追加しました");
});

async function removeRoom(room) {
  if (!confirm(`「${room.name}」を削除しますか？\n部屋の家具もすべて削除され、座っている人は「未出勤」に戻ります。`)) return;
  try {
    await officesApi.deleteRoom(room.id);
    await reload();
    showToast("部屋を削除しました");
  } catch (err) {
    showToast(err.message, "error");
  }
}

await reload();
