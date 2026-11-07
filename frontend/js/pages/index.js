// トップページは、ログイン状態に応じて適切な画面へ振り分けるだけ。
// （CSP でインラインスクリプトを禁止しているため、別ファイルにしている）

import { homePathFor, loadMe, PATHS } from "../lib/auth-guard.js";

const me = await loadMe();
window.location.replace(me ? homePathFor(me) : PATHS.login);
