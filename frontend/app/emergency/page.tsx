"use client";

import { EmergencyPanelClient } from "@/components/emergency/emergency-panel-client";
import { AppShell, useAccessState } from "@/components/layout/app-shell";

export default function EmergencyPage() {
  const { role, setRole, access } = useAccessState();

  return (
    <AppShell
      title="Emergency Response"
      description="Live incident response panel with evidence-backed report exports."
      role={role}
      access={access}
      onRoleChange={setRole}
    >
      <EmergencyPanelClient access={access} />
    </AppShell>
  );
}
