/** API の応答の型（app/schemas と対応させる）。 */

export type Role = "master" | "general";

export interface OrganizationSummary {
  id: number;
  name: string;
}

/** GET /api/v1/me */
export interface Me {
  id: number;
  email: string;
  role: Role;
  must_change_password: boolean;
  profile_completed: boolean;
  organization: OrganizationSummary;
}

/** GET /api/v1/organization */
export interface Organization {
  id: number;
  name: string;
  created_at: string;
}

/** エラーの応答 {"detail", "code", "errors"} の errors の1件 */
export interface FieldError {
  field: string;
  message: string;
}
