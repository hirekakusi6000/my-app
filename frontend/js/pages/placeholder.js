// まだ実装していない画面の仮表示。<body data-role="master|general"> で表示できる権限を指定する。

import { renderHeader } from "../components/app-header.js";
import { requireAuth } from "../lib/auth-guard.js";

const me = await requireAuth({ role: document.body.dataset.role });
renderHeader(document.getElementById("app-header"), me);
