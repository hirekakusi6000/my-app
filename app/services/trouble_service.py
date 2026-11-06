"""困りごとの共有。

- 登録できるのは一般ユーザー（プロフィール登録済み）
- 内容の変更・解決済みにするのは、登録した本人だけ
- 削除は本人とマスター（不適切な投稿を消せるように）
- 閲覧は同じ組織の全員
"""

import sqlite3

from app.core.errors import ForbiddenError, NotFoundError
from app.core.time import to_iso, utc_now
from app.entities.trouble import Trouble, TroubleStatus
from app.entities.user import User
from app.repositories.trouble_repository import TroubleRepository


class TroubleService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.troubles = TroubleRepository(conn)

    def list(
        self, viewer: User, *, status: TroubleStatus | None = None, user_id: int | None = None
    ) -> list[Trouble]:
        return self.troubles.list(viewer.organization_id, status=status, user_id=user_id)

    def create(self, author: User, *, title: str, body: str) -> Trouble:
        with self.conn:
            trouble_id = self.troubles.create(
                organization_id=author.organization_id,
                user_id=author.id,
                title=title,
                body=body,
                now=to_iso(utc_now()),
            )
        return self._get(author, trouble_id)

    def update(
        self,
        author: User,
        trouble_id: int,
        *,
        title: str | None = None,
        body: str | None = None,
        status: TroubleStatus | None = None,
    ) -> Trouble:
        trouble = self._get(author, trouble_id)
        if trouble.user_id != author.id:
            raise ForbiddenError("自分が登録した困りごとだけ変更できます")
        with self.conn:
            self.troubles.update(
                trouble_id=trouble.id,
                organization_id=author.organization_id,
                title=title if title is not None else trouble.title,
                body=body if body is not None else trouble.body,
                status=status if status is not None else trouble.status,
                now=to_iso(utc_now()),
            )
        return self._get(author, trouble_id)

    def delete(self, user: User, trouble_id: int) -> None:
        trouble = self._get(user, trouble_id)
        if not user.is_master and trouble.user_id != user.id:
            raise ForbiddenError("自分が登録した困りごとだけ削除できます")
        with self.conn:
            self.troubles.delete(trouble.id, user.organization_id)

    def _get(self, user: User, trouble_id: int) -> Trouble:
        trouble = self.troubles.get(trouble_id, user.organization_id)
        if trouble is None:
            raise NotFoundError("困りごとが見つかりません")
        return trouble
