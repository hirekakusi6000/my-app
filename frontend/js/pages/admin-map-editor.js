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

const stage = document.getElementById("stage");
const roomSelect = document.getElementById("room-select");
const statusEl = document.getElementById("status");
const props = document.getElementById("props");
const propsForm = props.querySelector("[data-form]");

// ───────── 状態 ─────────

let room = null; // 編集中の部屋
let items = []; // 家具（key は画面内だけで使う識別子）
let savedSnapshot = ""; // 保存済みの内容（変更があるかの判定に使う）
let selectedKey = null;
let nextKey = 1;
let svgParts = null;

const keyOf = () => `k${nextKey++}`;
const selected = () => items.find((i) => i.key === selectedKey) ?? null;
const snapshot = () =>
  JSON.stringify(items.map(({ key, ...rest }) => rest));
const isDirty = () => room !== null && snapshot() !== savedSnapshot;

function updateStatus() {
  statusEl.textContent = isDirty() ? "● 保存していない変更があります" : "保存済み";
  statusEl.classList.toggle("editor__status--dirty", isDirty());
}

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
  selectedKey = null;
  history.replaceState(null, "", `?room=${roomId}`);

  svgParts = createRoomSvg(room);
  svgParts.svg.classList.add("room-map--editable");
  svgParts.svg.style.width = `${room.width * CELL}px`;
  stage.replaceChildren(svgParts.svg);
  attachPointerHandlers(svgParts.svg);
  render();
}

// ───────── 描画 ─────────

function render() {
  const { furnitureLayer, overlayLayer } = svgParts;
  furnitureLayer.replaceChildren();
  overlayLayer.replaceChildren();
  for (const item of items) {
    const g = drawFurniture(item);
    g.dataset.key = item.key;
    if (item.key === selectedKey) g.classList.add("furniture--selected");
    furnitureLayer.append(g);
  }
  const sel = selected();
  if (sel) {
    const { w, h } = footprint(sel);
    overlayLayer.append(
      svgEl("rect", {
        x: sel.x * CELL - 2,
        y: sel.y * CELL - 2,
        width: w * CELL + 4,
        height: h * CELL + 4,
        class: "selection",
      }),
    );
    const handle = svgEl("rect", {
      x: (sel.x + w) * CELL - 7,
      y: (sel.y + h) * CELL - 7,
      width: 12,
      height: 12,
      class: "selection__handle",
    });
    handle.dataset.handle = "resize";
    overlayLayer.append(handle);
  }
  renderProps();
  updateStatus();
}

function renderProps() {
  const sel = selected();
  props.querySelector("[data-empty]").hidden = Boolean(sel);
  propsForm.hidden = !sel;
  if (!sel) return;
  props.querySelector("[data-type]").textContent = FURNITURE_TYPES[sel.type].label + (sel.type === "chair" ? "（座席）" : "");
  const f = propsForm.elements;
  // 入力中の欄は書き換えない（カーソル位置が飛ばないように）
  for (const name of ["label", "x", "y", "width", "height"]) {
    if (document.activeElement !== f[name]) f[name].value = sel[name] ?? "";
  }
}

// ───────── 配置の変更（すべてここを通して、はみ出しを防ぐ） ─────────

/** 変更後の家具が部屋に収まるなら反映して true を返す */
function apply(item, changes) {
  const next = { ...item, ...changes };
  const { w, h } = footprint(next);
  if (w < 1 || h < 1 || w > room.width || h > room.height) return false;
  next.x = Math.min(Math.max(0, next.x), room.width - w);
  next.y = Math.min(Math.max(0, next.y), room.height - h);
  Object.assign(item, next);
  return true;
}

function addItem(type) {
  const def = FURNITURE_TYPES[type];
  const item = { key: keyOf(), id: null, type, label: null, x: 0, y: 0, width: def.width, height: def.height, rotation: 0 };
  // 表示中の範囲の左上あたりに置く
  const visible = stage.getBoundingClientRect();
  const p = clientToGrid(svgParts.svg, visible.left + 40, visible.top + 40);
  if (!apply(item, { x: Math.round(p.x), y: Math.round(p.y) })) {
    showToast("部屋が小さすぎて追加できません", "error");
    return;
  }
  items.push(item);
  selectedKey = item.key;
  render();
}

function rotate(delta) {
  const sel = selected();
  if (!sel) return;
  const rotation = (sel.rotation + delta + 360) % 360;
  if (!apply(sel, { rotation })) showToast("部屋からはみ出すため回転できません", "error");
  render();
}

function removeSelected() {
  if (!selectedKey) return;
  items = items.filter((i) => i.key !== selectedKey);
  selectedKey = null;
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

// プロパティ欄
propsForm.addEventListener("input", (e) => {
  const sel = selected();
  if (!sel) return;
  const { name, value } = e.target;
  if (name === "label") {
    sel.label = value.trim() || null;
  } else {
    const n = Number(value);
    if (!Number.isInteger(n)) return;
    // 幅・奥行きは「向き0度のときの大きさ」として扱う
    if (!apply(sel, { [name]: n })) return;
  }
  render();
});
propsForm.addEventListener("change", () => renderProps()); // 補正された値を表示に戻す
propsForm.addEventListener("submit", (e) => e.preventDefault());
props.querySelectorAll("[data-rotate]").forEach((b) =>
  b.addEventListener("click", () => rotate(Number(b.dataset.rotate))),
);
props.querySelector("[data-delete]").addEventListener("click", removeSelected);

// ───────── マウス操作（移動・大きさの変更） ─────────

function attachPointerHandlers(svg) {
  let drag = null;

  svg.addEventListener("pointerdown", (e) => {
    const p = clientToGrid(svg, e.clientX, e.clientY);
    if (e.target.dataset?.handle === "resize" && selected()) {
      drag = { mode: "resize", item: selected() };
    } else {
      const g = e.target.closest("[data-key]");
      selectedKey = g ? g.dataset.key : null;
      const item = selected();
      if (item) drag = { mode: "move", item, dx: p.x - item.x, dy: p.y - item.y };
      render();
    }
    if (drag) svg.setPointerCapture(e.pointerId);
  });

  svg.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const p = clientToGrid(svg, e.clientX, e.clientY);
    const item = drag.item;
    if (drag.mode === "move") {
      apply(item, { x: Math.round(p.x - drag.dx), y: Math.round(p.y - drag.dy) });
    } else {
      const w = Math.max(1, Math.round(p.x - item.x));
      const h = Math.max(1, Math.round(p.y - item.y));
      const turned = item.rotation === 90 || item.rotation === 270;
      apply(item, turned ? { width: h, height: w } : { width: w, height: h });
    }
    render();
  });

  const end = () => {
    drag = null;
  };
  svg.addEventListener("pointerup", end);
  svg.addEventListener("pointercancel", end);
}

// ───────── キーボード操作 ─────────

document.addEventListener("keydown", (e) => {
  if (!selected() || e.target.closest("input, select, textarea, dialog")) return;
  const moves = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
  if (moves[e.key]) {
    e.preventDefault();
    const [dx, dy] = moves[e.key];
    const sel = selected();
    apply(sel, { x: sel.x + dx, y: sel.y + dy });
    render();
  } else if (e.key === "Delete" || e.key === "Backspace") {
    e.preventDefault();
    removeSelected();
  } else if (e.key === "r" || e.key === "R") {
    rotate(e.shiftKey ? -90 : 90);
  } else if (e.key === "Escape") {
    selectedKey = null;
    render();
  }
});

// ───────── 保存・元に戻す ─────────

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
    const keepSelectionIndex = items.findIndex((i) => i.key === selectedKey);
    items = layout.furniture.map((f) => ({ ...f, key: keyOf() }));
    savedSnapshot = snapshot();
    selectedKey = keepSelectionIndex >= 0 ? items[keepSelectionIndex]?.key ?? null : null;
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
