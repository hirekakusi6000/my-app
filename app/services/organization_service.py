"""組織の設定（名前の変更・削除）。マスターだけが操作できる。"""

import sqlite3

from app.core import security
from app.core.errors import BusinessRuleError
from app.entities.user import Organization, User
from app.repositories.organization_repository import OrganizationRepository
from app.services.avatar_storage import AvatarStorage


class OrganizationService:
    def __init__(self, conn: sqlite3.Connection, avatar_storage: AvatarStorage) -> None:
        self.conn = conn
        self.storage = avatar_storage
        self.organizations = OrganizationRepository(conn)

    def get(self, master: User) -> Organization:
        organization = self.organizations.get(master.organization_id)
        assert organization is not None  # users.organization_id は外部キーで保証されている
        return organization

    def rename(self, master: User, name: str) -> Organization:
        with self.conn:
            self.organizations.rename(master.organization_id, name)
        return self.get(master)

    def delete(self, master: User, *, password: str, confirm_name: str) -> None:
        """組織と、そこに含まれるすべてのデータを完全に削除する（元に戻せない）。

        誤操作を防ぐため、マスターのパスワードと組織名の入力を求める。
        """
        organization = self.get(master)
        if not security.verify_password(password, master.password_hash):
            raise BusinessRuleError("パスワードが違います", code="INVALID_PASSWORD")
        if confirm_name.strip() != organization.name:
            raise BusinessRuleError("組織名が一致しません", code="NAME_MISMATCH")

        avatar_paths = self.organizations.avatar_paths(organization.id)
        with self.conn:
            self.organizations.delete(organization.id)
        # DB から消えたことが確定してから、プロフィール画像のファイルを消す
        for path in avatar_paths:
            self.storage.delete(path)
