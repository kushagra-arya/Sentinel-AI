export type UserRole =
  | "admin"
  | "safety_officer"
  | "supervisor"
  | "compliance_officer"
  | "viewer";

export type AccessContext = {
  role: UserRole;
  assignedArea: string;
  readonly: boolean;
};

export const roleLabels: Record<UserRole, string> = {
  admin: "Admin",
  safety_officer: "Safety Officer",
  supervisor: "Supervisor",
  compliance_officer: "Compliance Officer",
  viewer: "Viewer"
};

export function defaultAccess(): AccessContext {
  return { role: "safety_officer", assignedArea: "Zone A", readonly: false };
}

export function accessForRole(role: UserRole): AccessContext {
  return {
    role,
    assignedArea: role === "supervisor" ? "Zone A" : "All Areas",
    readonly: role === "viewer" || role === "compliance_officer"
  };
}

export function canSeeArea(access: AccessContext, area: string | null | undefined): boolean {
  if (access.role !== "supervisor") {
    return true;
  }
  return !area || area === access.assignedArea;
}

export function canMutate(access: AccessContext): boolean {
  return !access.readonly && access.role !== "compliance_officer";
}
