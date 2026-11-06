// 技術スキルの入力欄。分類ごとに「スキル名＋経験年数」の行を追加・削除できる。

import { SKILL_CATEGORIES } from "../api/master-data.js";

/**
 * @param {HTMLElement} container
 * @param {any[]} candidates スキルの候補（GET /skills）
 * @param {{category: string, name: string, years: number}[]} value 登録済みのスキル
 */
export function renderSkillsEditor(container, candidates, value) {
  container.replaceChildren();
  container.classList.add("skills-editor");

  const lists = {};
  for (const { value: category, label } of SKILL_CATEGORIES) {
    const section = document.createElement("fieldset");
    section.className = "skills-editor__group";

    const legend = document.createElement("legend");
    legend.textContent = label;

    const datalist = document.createElement("datalist");
    datalist.id = `skill-options-${category}`;
    for (const s of candidates.filter((c) => c.category === category)) {
      const option = document.createElement("option");
      option.value = s.name;
      datalist.append(option);
    }

    const rows = document.createElement("div");
    rows.className = "skills-editor__rows";
    lists[category] = rows;

    const add = document.createElement("button");
    add.type = "button";
    add.className = "button button--ghost button--small";
    add.textContent = "＋ 追加";
    add.addEventListener("click", () => addRow(category).querySelector("input").focus());

    section.append(legend, datalist, rows, add);
    container.append(section);
  }

  function addRow(category, name = "", years = 1) {
    const row = document.createElement("div");
    row.className = "skills-editor__row";

    const nameInput = document.createElement("input");
    nameInput.className = "field__input";
    nameInput.type = "text";
    nameInput.maxLength = 50;
    nameInput.placeholder = "スキル名";
    nameInput.setAttribute("list", `skill-options-${category}`);
    nameInput.value = name;
    nameInput.dataset.role = "name";

    const yearsInput = document.createElement("input");
    yearsInput.className = "field__input skills-editor__years";
    yearsInput.type = "number";
    yearsInput.min = "0";
    yearsInput.max = "50";
    yearsInput.value = String(years);
    yearsInput.dataset.role = "years";

    const unit = document.createElement("span");
    unit.textContent = "年";

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "button button--ghost button--small";
    remove.textContent = "削除";
    remove.addEventListener("click", () => row.remove());

    row.append(nameInput, yearsInput, unit, remove);
    lists[category].append(row);
    return row;
  }

  for (const s of value) addRow(s.category, s.name, s.years);

  return {
    /** 入力内容を返す。不正な値があれば例外（メッセージ付き）を投げる */
    getValue() {
      const result = [];
      const seen = new Set();
      for (const [category, rows] of Object.entries(lists)) {
        for (const row of rows.children) {
          const name = row.querySelector('[data-role="name"]').value.trim();
          const yearsText = row.querySelector('[data-role="years"]').value;
          if (!name) continue; // 空の行は無視する
          const years = Number(yearsText);
          if (!Number.isInteger(years) || years < 0 || years > 50) {
            throw new Error(`「${name}」の経験年数は0〜50の整数で入力してください`);
          }
          const key = `${category}:${name.toLowerCase()}`;
          if (seen.has(key)) throw new Error(`「${name}」が重複しています`);
          seen.add(key);
          result.push({ category, name, years });
        }
      }
      return result;
    },
  };
}
