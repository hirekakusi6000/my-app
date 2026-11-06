// 初期パスワードの自動生成。見間違えやすい文字（0/O、1/l/I など）は使わない。

const CHARS = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789";

export function generatePassword(length = 12) {
  const values = new Uint32Array(length);
  crypto.getRandomValues(values);
  return Array.from(values, (v) => CHARS[v % CHARS.length]).join("");
}
