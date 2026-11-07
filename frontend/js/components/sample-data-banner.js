// まだ何もない組織のマスターに、お試し用のサンプルデータの作成を案内する。

import { organizationApi } from "../api/organization.js";
import { showToast } from "../lib/toast.js";

/**
 * サンプルを作成できる場合だけ、container にお知らせを表示する。
 * @param {HTMLElement} container
 * @param {{ onCreated?: () => void }} options
 */
export async function renderSampleDataBanner(container, { onCreated } = {}) {
  let status;
  try {
    status = await organizationApi.sampleDataStatus();
  } catch {
    return; // 表示できなくても画面の他の機能には影響させない
  }
  if (!status.available) {
    container.hidden = true;
    return;
  }

  container.className = "sample-banner";
  container.innerHTML = `
    <div class="sample-banner__text">
      <strong>まずはサンプルで試してみませんか？</strong>
      <span>机と椅子を並べたオフィスマップと、プロフィール・スキル・在席状態を登録した従業員6人をまとめて作成します。</span>
    </div>
    <button type="button" class="button">サンプルを作成</button>
  `;
  container.hidden = false;

  const button = container.querySelector("button");
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await organizationApi.createSampleData();
      container.hidden = true;
      showToast("サンプルデータを作成しました");
      onCreated?.();
    } catch (err) {
      showToast(err.message, "error");
      button.disabled = false;
    }
  });
}
