// マップから座席（椅子）を1つ選ぶダイアログ。

import { officesApi } from "../api/offices.js";
import { CELL, createRoomSvg, drawFurniture } from "./map-renderer.js";

/**
 * @param {{ currentSeatId: number | null, currentRoomId?: number | null, title?: string }} options
 * @returns {Promise<{ seatId: number | null } | null>} 選んだ座席（null は「設定を外す」）。キャンセル時は null
 */
export async function pickSeat({ currentSeatId, currentRoomId = null, title = "座席を選ぶ" }) {
  const floors = await officesApi.listFloors();
  const rooms = floors.flatMap((f) => f.rooms.map((r) => ({ ...r, floorName: f.name })));

  const dialog = document.createElement("dialog");
  dialog.className = "dialog seat-picker";
  dialog.innerHTML = `
    <h2 class="dialog__title"></h2>
    <div class="seat-picker__toolbar">
      <select class="field__input" aria-label="部屋"></select>
      <span class="field__hint" data-hint>椅子をクリックして選んでください</span>
    </div>
    <div class="seat-picker__stage"></div>
    <div class="dialog__actions">
      <button type="button" class="button button--ghost button--danger-text" data-clear>設定を外す</button>
      <span class="editor__spacer"></span>
      <button type="button" class="button button--ghost" data-cancel>キャンセル</button>
      <button type="button" class="button" data-ok disabled>この座席にする</button>
    </div>
  `;
  dialog.querySelector(".dialog__title").textContent = title;
  document.body.append(dialog);

  const select = dialog.querySelector("select");
  const stage = dialog.querySelector(".seat-picker__stage");
  const ok = dialog.querySelector("[data-ok]");
  dialog.querySelector("[data-clear]").hidden = currentSeatId === null;

  if (rooms.length === 0) {
    stage.textContent = "まだオフィスマップがありません。管理者がマップを作成すると選べるようになります。";
    select.hidden = true;
    dialog.querySelector("[data-hint]").hidden = true;
  }

  for (const f of floors) {
    if (!f.rooms.length) continue;
    const group = document.createElement("optgroup");
    group.label = f.name;
    for (const r of f.rooms) group.append(new Option(r.name, r.id));
    select.append(group);
  }

  let picked = currentSeatId;

  async function showRoom(roomId) {
    const layout = await officesApi.getLayout(roomId);
    const { svg, furnitureLayer } = createRoomSvg(layout.room);
    svg.classList.add("room-map--pickable");
    svg.style.width = `${layout.room.width * CELL}px`;
    for (const item of layout.furniture) {
      const g = drawFurniture(item);
      if (item.type === "chair") {
        g.dataset.seatId = item.id;
        if (item.id === picked) g.classList.add("furniture--picked");
        g.addEventListener("click", () => {
          picked = item.id;
          furnitureLayer.querySelectorAll(".furniture--picked").forEach((x) => x.classList.remove("furniture--picked"));
          g.classList.add("furniture--picked");
          ok.disabled = false;
        });
      }
      furnitureLayer.append(g);
    }
    stage.replaceChildren(svg);
    if (!layout.furniture.some((f) => f.type === "chair")) {
      const note = document.createElement("p");
      note.className = "field__hint";
      note.textContent = "この部屋には椅子がありません。";
      stage.append(note);
    }
  }

  if (rooms.length) {
    const initial = rooms.some((r) => r.id === currentRoomId) ? currentRoomId : rooms[0].id;
    select.value = String(initial);
    await showRoom(initial);
    select.addEventListener("change", () => showRoom(Number(select.value)));
  }

  dialog.showModal();
  return new Promise((resolve) => {
    const finish = (result) => {
      dialog.close();
      dialog.remove();
      resolve(result);
    };
    dialog.querySelector("[data-ok]").addEventListener("click", () => finish({ seatId: picked }));
    dialog.querySelector("[data-clear]").addEventListener("click", () => finish({ seatId: null }));
    dialog.querySelector("[data-cancel]").addEventListener("click", () => finish(null));
    dialog.addEventListener("cancel", (e) => {
      e.preventDefault();
      finish(null);
    });
  });
}
