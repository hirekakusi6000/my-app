import { officesApi } from "../api/offices.js";
import { renderHeader } from "../components/app-header.js";
import {
  CELL,
  clientToGrid,
  createRoomSvg,
  drawFurniture,
  footprint,
  FURNITURE_TYPES,
  svgEl,
} from "../components/map-renderer.js";
import { requireAuth } from "../lib/auth-guard.js";
import { showToast } from "../lib/toast.js";

const me = await requireAuth({ role: "master" });
renderHeader(document.getElementById("app-header"), me);

const MAX_HISTORY = 100;

const stage = document.getElementById("stage");
const roomSelect = document.getElementById("room-select");
const statusEl = document.getElementById("status");
const props = document.getElementById("props");
const selectionPanel = props.querySelector("[data-selection]");
const propsForm = props.querySelector("[data-form]");
const undoButton = document.getElementById("undo");
const redoButton = document.getElementById("redo");

// ───────── 状態 ─────────

let room = null; // 編集中の部屋
let items = []; // 家具（key は画面内だけで使う識別子）
let savedSnapshot = ""; // 保存済みの内容（変更があるかの判定に使う）
let selection = new Set(); // 選択中の家具の key
let nextKey = 1;
let svgParts = null;
let undoStack = []; // 変更前の items の写し
let redoStack = [];
let clipboard = []; // コピーした家具（id と key は持たない）
let pasteCount = 0; // 同じものを続けて貼り付けたときに、少しずつずらすため

const keyOf = () => `k${nextKey++}`;
const selectedItems = () => items.filter((i) => selection.has(i.key));
const single = () => (selection.size === 1 ? selectedItems()[0] : null);
const snapshot = () => JSON.stringify(items.map(({ key, ...rest }) => rest));
const isDirty = () => room !== null && snapshot() !== savedSnapshot;
const cloneItems = (list) => list.map((i) => ({ ...i }));

function updateStatus() {
  statusEl.textContent = isDirty() ? "● 保存していない変更があります" : "保存済み";
  statusEl.classList.toggle("editor__status--dirty", isDirty());
  undoButton.disabled = undoStack.length === 0;
  redoButton.disabled = redoStack.length === 0;
}

// ───────── 元に戻す・やり直し ─────────

/** 変更する直前の状態を記録する（「元に戻す」で戻れるように） */
function checkpoint(before = cloneItems(items)) {
  undoStack.push(before);
  if (undoStack.length > MAX_HISTORY) undoStack.shift();
  redoStack = [];
}

function restore(state) {
  items = cloneItems(state);
  // 消えた家具は選択から外す
  const keys = new Set(items.map((i) => i.key));
  selection = new Set([...selection].filter((k) => keys.has(k)));
  render();
}

function undo() {
  if (!undoStack.length) return;
  redoStack.push(cloneItems(items));
  restore(undoStack.pop());
}

function redo() {
  if (!redoStack.length) return;
  undoStack.push(cloneItems(items));
  restore(redoStack.pop());
}

undoButton.addEventListener("click", undo);
redoButton.addEventListener("click", redo);

// ───────── 部屋の選択と読み込み ─────────

const floors = await officesApi.listFloors();
const allRooms = floors.flatMap((f) => f.rooms.map((r) => ({ ...r, floorName: f.name })));

if (allRooms.length === 0) {
  stage.innerHTML = "";
  const empty = document.createElement("div");
  empty.className = "empty-state";
  empty.innerHTML = '<p>まだ部屋がありません。</p><a class="button" href="/admin/offices.html">フロア・部屋を作成する</a>';
  stage.append(empty);
  document.getElementById("save").disabled = true;
  document.getElementById("revert").disabled = true;
} else {
  for (const f of floors) {
    if (!f.rooms.length) continue;
    const group = document.createElement("optgroup");
    group.label = f.name;
    for (const r of f.rooms) group.append(new Option(r.name, r.id));
    roomSelect.append(group);
  }
  const fromUrl = Number(new URLSearchParams(location.search).get("room"));
  const initial = allRooms.some((r) => r.id === fromUrl) ? fromUrl : allRooms[0].id;
  roomSelect.value = String(initial);
  await loadRoom(initial);
}

roomSelect.addEventListener("change", async () => {
  if (isDirty() && !confirm("保存していない変更があります。破棄して別の部屋に切り替えますか？")) {
    roomSelect.value = String(room.id);
    return;
  }
  await loadRoom(Number(roomSelect.value));
});

async function loadRoom(roomId) {
  const layout = await officesApi.getLayout(roomId);
  room = layout.room;
  items = layout.furniture.map((f) => ({ ...f, key: keyOf() }));
  savedSnapshot = snapshot();
  selection = new Set();
  undoStack = [];
  redoStack = [];
  window.history.replaceState(null, "", `?room=${roomId}`);

  svgParts = createRoomSvg(room);
  svgParts.svg.classList.add("room-map--editable");
  svgParts.svg.style.width = `${room.width * CELL}px`;
  stage.replaceChildren(svgParts.svg);
  attachPointerHandlers(svgParts.svg);
  render();
}

// ───────── 描画 ─────────

function render(marquee = null) {
  const { furnitureLayer, overlayLayer } = svgParts;
  furnitureLayer.replaceChildren();
  overlayLayer.replaceChildren();
  for (const item of items) {
    const g = drawFurniture(item);
    g.dataset.key = item.key;
    if (selection.has(item.key)) g.classList.add("furniture--selected");
    furnitureLayer.append(g);
  }
  for (const item of selectedItems()) {
    const { w, h } = footprint(item);
    overlayLayer.append(
      svgEl("rect", {
        x: item.x * CELL - 2,
        y: item.y * CELL - 2,
        width: w * CELL + 4,
        height: h * CELL + 4,
        class: "selection",
      }),
    );
  }
  // 大きさの変更は、1つだけ選んでいるときにできる
  const one = single();
  if (one) {
    const { w, h } = footprint(one);
    const handle = svgEl("rect", {
      x: (one.x + w) * CELL - 7,
      y: (one.y + h) * CELL - 7,
      width: 12,
      height: 12,
      class: "selection__handle",
    });
    handle.dataset.handle = "resize";
    overlayLayer.append(handle);
  }
  if (marquee) {
    overlayLayer.append(
      svgEl("rect", {
        x: Math.min(marquee.x1, marquee.x2) * CELL,
        y: Math.min(marquee.y1, marquee.y2) * CELL,
        width: Math.abs(marquee.x2 - marquee.x1) * CELL,
        height: Math.abs(marquee.y2 - marquee.y1) * CELL,
        class: "marquee",
      }),
    );
  }
  renderProps();
  updateStatus();
}

function renderProps() {
  const count = selection.size;
  props.querySelector("[data-empty]").hidden = count > 0;
  selectionPanel.hidden = count === 0;
  if (count === 0) return;

  const one = single();
  propsForm.hidden = !one;
  if (!one) {
    props.querySelector("[data-type]").textContent = `${count}個を選択中`;
    return;
  }
  props.querySelector("[data-type]").textContent =
    FURNITURE_TYPES[one.type].label + (one.type === "chair" ? "（座席）" : "");
  const f = propsForm.elements;
  // 入力中の欄は書き換えない（カーソル位置が飛ばないように）
  for (const name of ["label", "x", "y", "width", "height"]) {
    if (document.activeElement !== f[name]) f[name].value = one[name] ?? "";
  }
}

// ───────── 配置の変更（すべてここを通して、はみ出しを防ぐ） ─────────

function fits(item) {
  const { w, h } = footprint(item);
  return w >= 1 && h >= 1 && w <= room.width && h <= room.height;
}

function clampInto(item) {
  const { w, h } = footprint(item);
  item.x = Math.min(Math.max(0, item.x), room.width - w);
  item.y = Math.min(Math.max(0, item.y), room.height - h);
}

/** 変更後の家具が部屋に収まるなら反映して true を返す */
function apply(item, changes) {
  const next = { ...item, ...changes };
  if (!fits(next)) return false;
  clampInto(next);
  Object.assign(item, next);
  return true;
}

/** 選んだ家具をまとめて動かす。部屋からはみ出さない範囲に動く量を抑える */
function moveGroup(group, dx, dy, origins = null) {
  let [minDx, maxDx, minDy, maxDy] = [-Infinity, Infinity, -Infinity, Infinity];
  for (const item of group) {
    const o = origins?.get(item.key) ?? item;
    const { w, h } = footprint(item);
    minDx = Math.max(minDx, -o.x);
    maxDx = Math.min(maxDx, room.width - w - o.x);
    minDy = Math.max(minDy, -o.y);
    maxDy = Math.min(maxDy, room.height - h - o.y);
  }
  const cdx = Math.min(Math.max(dx, minDx), maxDx);
  const cdy = Math.min(Math.max(dy, minDy), maxDy);
  for (const item of group) {
    const o = origins?.get(item.key) ?? { x: item.x, y: item.y };
    item.x = o.x + cdx;
    item.y = o.y + cdy;
  }
}

function addItem(type) {
  const def = FURNITURE_TYPES[type];
  const item = { key: keyOf(), id: null, type, label: null, x: 0, y: 0, width: def.width, height: def.height, rotation: 0 };
  // 表示中の範囲の左上あたりに置く
  const visible = stage.getBoundingClientRect();
  const p = clientToGrid(svgParts.svg, visible.left + 40, visible.top + 40);
  const before = cloneItems(items);
  if (!apply(item, { x: Math.round(p.x), y: Math.round(p.y) })) {
    showToast("部屋が小さすぎて追加できません", "error");
    return;
  }
  checkpoint(before);
  items.push(item);
  selection = new Set([item.key]);
  render();
}

function rotateSelected(delta) {
  const group = selectedItems();
  if (!group.length) return;
  const before = cloneItems(items);
  // 1つでも回転できない家具があれば、どれも回転しない
  const rotated = group.map((item) => ({ ...item, rotation: (item.rotation + delta + 360) % 360 }));
  if (!rotated.every(fits)) {
    showToast("部屋からはみ出すため回転できません", "error");
    return;
  }
  checkpoint(before);
  for (const [i, item] of group.entries()) {
    item.rotation = rotated[i].rotation;
    clampInto(item);
  }
  render();
}

function removeSelected() {
  if (!selection.size) return;
  checkpoint();
  items = items.filter((i) => !selection.has(i.key));
  selection = new Set();
  render();
}

function copySelected() {
  const group = selectedItems();
  if (!group.length) return false;
  clipboard = group.map(({ key, id, ...rest }) => ({ ...rest }));
  pasteCount = 0;
  return true;
}

function paste() {
  if (!clipboard.length || !room) return;
  pasteCount += 1;
  const pasted = clipboard
    .map((c) => ({ ...c, id: null, key: keyOf(), x: c.x + pasteCount, y: c.y + pasteCount }))
    .filter(fits);
  if (!pasted.length) {
    showToast("部屋が小さすぎて貼り付けられません", "error");
    return;
  }
  checkpoint();
  // 元の並びを保ったまま、部屋の中に収まるように全体をずらす
  const origins = new Map(pasted.map((p) => [p.key, { x: p.x, y: p.y }]));
  moveGroup(pasted, 0, 0, origins);
  items.push(...pasted);
  selection = new Set(pasted.map((p) => p.key));
  render();
}

function duplicateSelected() {
  if (copySelected()) paste();
}

function selectAll() {
  selection = new Set(items.map((i) => i.key));
  render();
}

// パレット
const palette = document.getElementById("palette");
for (const [type, def] of Object.entries(FURNITURE_TYPES)) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = `palette-item palette-item--${type}`;
  b.textContent = def.label;
  b.addEventListener("click", () => room && addItem(type));
  palette.append(b);
}

// プロパティ欄（1つだけ選んでいるとき）
let editBefore = null; // 入力を始める前の状態（入力をまとめて1回の「元に戻す」にする）
propsForm.addEventListener("focusin", () => {
  editBefore = cloneItems(items);
});
propsForm.addEventListener("input", (e) => {
  const one = single();
  if (!one) return;
  const { name, value } = e.target;
  if (name === "label") {
    one.label = value.trim() || null;
  } else {
    const n = Number(value);
    if (!Number.isInteger(n)) return;
    // 幅・奥行きは「向き0度のときの大きさ」として扱う
    if (!apply(one, { [name]: n })) return;
  }
  render();
});
propsForm.addEventListener("change", () => {
  if (editBefore && JSON.stringify(editBefore) !== JSON.stringify(items)) checkpoint(editBefore);
  editBefore = cloneItems(items);
  renderProps(); // 補正された値を表示に戻す
  updateStatus();
});
propsForm.addEventListener("submit", (e) => e.preventDefault());
props.querySelectorAll("[data-rotate]").forEach((b) =>
  b.addEventListener("click", () => rotateSelected(Number(b.dataset.rotate))),
);
props.querySelector("[data-delete]").addEventListener("click", removeSelected);
props.querySelector("[data-duplicate]").addEventListener("click", duplicateSelected);

// ───────── マウス操作（選択・移動・大きさの変更・範囲選択） ─────────

function attachPointerHandlers(svg) {
  let drag = null;

  svg.addEventListener("pointerdown", (e) => {
    const p = clientToGrid(svg, e.clientX, e.clientY);
    const before = cloneItems(items);

    if (e.target.dataset?.handle === "resize" && single()) {
      drag = { mode: "resize", item: single(), before };
    } else {
      const g = e.target.closest("[data-key]");
      const key = g?.dataset.key;
      if (key && e.shiftKey) {
        // Shift+クリック：選択に追加・解除（ドラッグはしない）
        if (selection.has(key)) selection.delete(key);
        else selection.add(key);
        render();
        return;
      }
      if (key) {
        // 選択していない家具を押したら、その家具だけを選ぶ。選択中の家具ならまとめて動かす
        if (!selection.has(key)) selection = new Set([key]);
        const group = selectedItems();
        drag = {
          mode: "move",
          group,
          start: p,
          origins: new Map(group.map((i) => [i.key, { x: i.x, y: i.y }])),
          before,
        };
      } else {
        // 何もない所：範囲選択を始める（Shift を押していれば今の選択に追加）
        drag = {
          mode: "marquee",
          base: e.shiftKey ? new Set(selection) : new Set(),
          box: { x1: p.x, y1: p.y, x2: p.x, y2: p.y },
        };
        selection = new Set(drag.base);
      }
      render();
    }
    try {
      // 部屋の外までドラッグしても追いかけられるようにする
      svg.setPointerCapture(e.pointerId);
    } catch {
      // 対応していない入力（一部のペンや自動操作など）では、捕まえずに続ける
    }
  });

  svg.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const p = clientToGrid(svg, e.clientX, e.clientY);
    if (drag.mode === "move") {
      moveGroup(drag.group, Math.round(p.x - drag.start.x), Math.round(p.y - drag.start.y), drag.origins);
      render();
    } else if (drag.mode === "resize") {
      const item = drag.item;
      const w = Math.max(1, Math.round(p.x - item.x));
      const h = Math.max(1, Math.round(p.y - item.y));
      const turned = item.rotation === 90 || item.rotation === 270;
      apply(item, turned ? { width: h, height: w } : { width: w, height: h });
      render();
    } else {
      selectInBox(p);
      render(drag.box);
    }
  });

  /** 範囲選択の枠を p まで広げ、枠に少しでも重なった家具を選ぶ */
  function selectInBox(p) {
    drag.box.x2 = p.x;
    drag.box.y2 = p.y;
    const [x1, x2] = [Math.min(drag.box.x1, p.x), Math.max(drag.box.x1, p.x)];
    const [y1, y2] = [Math.min(drag.box.y1, p.y), Math.max(drag.box.y1, p.y)];
    const hit = items.filter((i) => {
      const { w, h } = footprint(i);
      return i.x < x2 && i.x + w > x1 && i.y < y2 && i.y + h > y1;
    });
    selection = new Set([...drag.base, ...hit.map((i) => i.key)]);
  }

  const end = (e) => {
    // 指を離した位置でも範囲を確定する（移動のイベントが少ない環境でも選べるように）
    if (drag?.mode === "marquee") selectInBox(clientToGrid(svg, e.clientX, e.clientY));
    if (drag?.before && JSON.stringify(drag.before) !== JSON.stringify(items)) {
      checkpoint(drag.before);
    }
    drag = null;
    render();
  };
  svg.addEventListener("pointerup", end);
  svg.addEventListener("pointercancel", end);
}

// ───────── キーボード操作 ─────────

document.addEventListener("keydown", (e) => {
  // 入力欄で文字を打っているときは、ショートカットとして扱わない
  const typing = e.target instanceof Element && e.target.closest("input, select, textarea, dialog");
  if (!room || typing) return;
  const ctrl = e.ctrlKey || e.metaKey;
  const key = e.key.toLowerCase();

  if (ctrl) {
    const actions = {
      z: () => (e.shiftKey ? redo() : undo()),
      y: redo,
      c: () => copySelected() && showToast(`${clipboard.length}個をコピーしました`),
      v: paste,
      d: duplicateSelected,
      a: selectAll,
    };
    if (actions[key]) {
      e.preventDefault();
      actions[key]();
    }
    return;
  }

  if (!selection.size) return;
  const moves = { arrowleft: [-1, 0], arrowright: [1, 0], arrowup: [0, -1], arrowdown: [0, 1] };
  if (moves[key]) {
    e.preventDefault();
    checkpoint();
    moveGroup(selectedItems(), ...moves[key]);
    render();
  } else if (key === "delete" || key === "backspace") {
    e.preventDefault();
    removeSelected();
  } else if (key === "r") {
    rotateSelected(e.shiftKey ? -90 : 90);
  } else if (key === "escape") {
    selection = new Set();
    render();
  }
});

// ───────── 保存・保存時の状態に戻す ─────────

document.getElementById("save").addEventListener("click", async (e) => {
  if (!room) return;
  const button = e.currentTarget;
  // 座っている人がいる椅子を削除しようとしていないか確認する
  const before = JSON.parse(savedSnapshot);
  const keptIds = new Set(items.filter((i) => i.type === "chair" && i.id).map((i) => i.id));
  const removedChairIds = before.filter((f) => f.type === "chair" && !keptIds.has(f.id)).map((f) => f.id);
  if (removedChairIds.length) {
    const occupants = await officesApi.getOccupancy(room.id).catch(() => []);
    const affected = occupants.filter((o) => removedChairIds.includes(o.seat_id));
    if (
      affected.length &&
      !confirm(
        `次の人が座っている椅子を削除します。保存すると、この人たちは「未出勤」に戻ります。\n\n` +
          affected.map((o) => `・${o.name ?? "名前未登録"}`).join("\n"),
      )
    ) {
      return;
    }
  }

  button.disabled = true;
  try {
    const payload = items.map(({ key, ...rest }) => rest);
    const layout = await officesApi.saveLayout(room.id, payload);
    // 保存後も同じ家具を選んだままにする（並び順は送った順のまま返ってくる）
    const selectedIndexes = items.flatMap((i, idx) => (selection.has(i.key) ? [idx] : []));
    items = layout.furniture.map((f) => ({ ...f, key: keyOf() }));
    savedSnapshot = snapshot();
    selection = new Set(selectedIndexes.map((idx) => items[idx]?.key).filter(Boolean));
    // 保存前の状態には id のない家具が含まれるので、履歴はここで区切る
    undoStack = [];
    redoStack = [];
    render();
    showToast("配置を保存しました");
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    button.disabled = false;
  }
});

document.getElementById("revert").addEventListener("click", async () => {
  if (!room || !isDirty()) return;
  if (!confirm("保存していない変更を破棄して、保存済みの配置に戻しますか？")) return;
  await loadRoom(room.id);
});

window.addEventListener("beforeunload", (e) => {
  if (isDirty()) e.preventDefault();
});
