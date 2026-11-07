// 部屋のマップを SVG で描く共通部品（閲覧・編集・座席選択で使う）。
//
// 座標はグリッドの単位。家具の x, y は「床に占める範囲」の左上で、
// 向きが 90 度・270 度のときは幅と奥行きが入れ替わる（サーバー側の定義と同じ）。

const SVG_NS = "http://www.w3.org/2000/svg";

/** 1マスの大きさ（px） */
export const CELL = 32;

export const FURNITURE_TYPES = {
  desk: { label: "机", width: 4, height: 2 },
  chair: { label: "椅子", width: 1, height: 1 },
  wall: { label: "壁", width: 6, height: 1 },
  door: { label: "ドア", width: 2, height: 1 },
  other: { label: "その他", width: 2, height: 2 },
};

/** 「前日から更新なし」の説明（最終更新の日時つき） */
export function staleLabel(updatedAt) {
  const when = new Date(updatedAt).toLocaleString("ja-JP", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  return `前日から更新なし（最終更新 ${when}）`;
}

export const STATUS_LABELS = {
  present: "在席中",
  away: "離席中",
  remote: "リモート",
  not_working: "未出勤",
};

export function svgEl(tag, attrs = {}) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v));
  return el;
}

/** 床に占める範囲の { w, h }（グリッド単位） */
export function footprint(item) {
  return item.rotation === 90 || item.rotation === 270
    ? { w: item.height, h: item.width }
    : { w: item.width, h: item.height };
}

/** 画面上の座標をグリッドの座標（小数）に変換する */
export function clientToGrid(svg, clientX, clientY) {
  const point = svg.createSVGPoint();
  point.x = clientX;
  point.y = clientY;
  const p = point.matrixTransform(svg.getScreenCTM().inverse());
  return { x: p.x / CELL, y: p.y / CELL };
}

/**
 * 部屋の SVG を作る。
 * @returns {{ svg: SVGSVGElement, furnitureLayer: SVGGElement, overlayLayer: SVGGElement }}
 */
export function createRoomSvg(room) {
  const width = room.width * CELL;
  const height = room.height * CELL;
  const svg = svgEl("svg", {
    viewBox: `0 0 ${width} ${height}`,
    class: "room-map",
    role: "img",
    "aria-label": `${room.name} のマップ`,
  });

  const defs = svgEl("defs");
  const pattern = svgEl("pattern", {
    id: "grid",
    width: CELL,
    height: CELL,
    patternUnits: "userSpaceOnUse",
  });
  pattern.append(svgEl("path", { d: `M ${CELL} 0 L 0 0 0 ${CELL}`, class: "room-map__grid" }));
  defs.append(pattern);
  svg.append(defs);

  svg.append(svgEl("rect", { x: 0, y: 0, width, height, class: "room-map__floor" }));
  svg.append(svgEl("rect", { x: 0, y: 0, width, height, fill: "url(#grid)" }));
  svg.append(svgEl("rect", { x: 0, y: 0, width, height, class: "room-map__border" }));

  const furnitureLayer = svgEl("g");
  const overlayLayer = svgEl("g");
  svg.append(furnitureLayer, overlayLayer);
  return { svg, furnitureLayer, overlayLayer };
}

/** 家具を1つ描いた <g> を返す */
export function drawFurniture(item) {
  const { w, h } = footprint(item);
  const x = item.x * CELL;
  const y = item.y * CELL;
  const pw = w * CELL;
  const ph = h * CELL;
  const g = svgEl("g", { class: `furniture furniture--${item.type}` });

  if (item.type === "chair") {
    const inset = 4;
    g.append(
      svgEl("rect", {
        x: x + inset,
        y: y + inset,
        width: pw - inset * 2,
        height: ph - inset * 2,
        rx: 6,
        class: "furniture__body",
      }),
    );
    // 背もたれ（向きによって位置が変わる）
    const t = 5;
    const back = {
      0: { x: x + inset, y: y + inset, width: pw - inset * 2, height: t },
      90: { x: x + pw - inset - t, y: y + inset, width: t, height: ph - inset * 2 },
      180: { x: x + inset, y: y + ph - inset - t, width: pw - inset * 2, height: t },
      270: { x: x + inset, y: y + inset, width: t, height: ph - inset * 2 },
    }[item.rotation];
    g.append(svgEl("rect", { ...back, rx: 2, class: "furniture__back" }));
  } else if (item.type === "door") {
    g.append(svgEl("rect", { x, y, width: pw, height: ph, class: "furniture__body" }));
    // 開く向きの目印（扉の軌跡）
    const r = Math.min(pw, ph);
    const arc = {
      0: `M ${x} ${y + ph} A ${r} ${r} 0 0 1 ${x + r} ${y + ph - r}`,
      90: `M ${x} ${y} A ${r} ${r} 0 0 1 ${x + r} ${y + r}`,
      180: `M ${x + pw} ${y} A ${r} ${r} 0 0 1 ${x + pw - r} ${y + r}`,
      270: `M ${x + pw} ${y + ph} A ${r} ${r} 0 0 1 ${x + pw - r} ${y + ph - r}`,
    }[item.rotation];
    g.append(svgEl("path", { d: arc, class: "furniture__swing" }));
  } else {
    g.append(
      svgEl("rect", {
        x,
        y,
        width: pw,
        height: ph,
        rx: item.type === "desk" ? 4 : 0,
        class: "furniture__body",
      }),
    );
  }

  const text = item.label || (item.type === "chair" || item.type === "wall" ? "" : FURNITURE_TYPES[item.type].label);
  if (text) {
    const label = svgEl("text", {
      x: x + pw / 2,
      y: y + ph / 2,
      class: "furniture__label",
      "dominant-baseline": "central",
      "text-anchor": "middle",
    });
    label.textContent = text;
    g.append(label);
  }
  return g;
}

/**
 * 座っている人のアイコンを描く。
 * @param {SVGGElement} layer
 * @param {Map<number, any>} seats 座席 id → 家具
 * @param {any[]} occupants GET /rooms/{id}/occupancy
 * @param {(occupant: any) => void} onClick
 */
export function drawOccupants(layer, seats, occupants, onClick) {
  layer.replaceChildren();
  for (const o of occupants) {
    const seat = seats.get(o.seat_id);
    if (!seat) continue;
    const { w, h } = footprint(seat);
    const cx = (seat.x + w / 2) * CELL;
    const cy = (seat.y + h / 2) * CELL;
    const r = CELL * 0.62;

    const g = svgEl("g", {
      class: `occupant occupant--${o.status}${o.is_stale ? " occupant--stale" : ""}`,
      tabindex: 0,
      role: "button",
      "aria-label": `${o.name ?? "名前未登録"}（${STATUS_LABELS[o.status] ?? o.status}）`,
    });
    g.dataset.seatId = o.seat_id;
    const title = svgEl("title");
    title.textContent = `${o.name ?? ""}（${STATUS_LABELS[o.status] ?? o.status}）`;
    if (o.is_stale) title.textContent += `
${staleLabel(o.updated_at)}`;
    g.append(title);

    g.append(svgEl("circle", { cx, cy, r: r + 3, class: "occupant__ring" }));
    if (o.avatar_url) {
      const clipId = `clip-occupant-${o.seat_id}`;
      const clip = svgEl("clipPath", { id: clipId });
      clip.append(svgEl("circle", { cx, cy, r }));
      g.append(clip);
      g.append(
        svgEl("image", {
          href: o.avatar_url,
          x: cx - r,
          y: cy - r,
          width: r * 2,
          height: r * 2,
          "clip-path": `url(#${clipId})`,
          preserveAspectRatio: "xMidYMid slice",
        }),
      );
    } else {
      g.append(svgEl("circle", { cx, cy, r, class: "occupant__face" }));
      const initial = svgEl("text", {
        x: cx,
        y: cy,
        class: "occupant__initial",
        "dominant-baseline": "central",
        "text-anchor": "middle",
      });
      initial.textContent = (o.name ?? "?").trim().charAt(0);
      g.append(initial);
    }

    const nameTag = svgEl("text", {
      x: cx,
      y: cy + r + 12,
      class: "occupant__name",
      "text-anchor": "middle",
    });
    nameTag.textContent = o.name ?? "";
    g.append(nameTag);

    g.addEventListener("click", () => onClick(o));
    g.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onClick(o);
      }
    });
    layer.append(g);
  }
}
