"use client";

import { DashboardClient } from "@/app/dashboard/dashboard-client";
import { AppShell, useAccessState } from "@/components/layout/app-shell";

export default function DashboardPage() {
  const { role, setRole, access } = useAccessState();

  return (
    <AppShell
      title="Dashboard"
      description="Risk score, alerts, telemetry trends, heatmap, timeline, and response actions."
      role={role}
      access={access}
      onRoleChange={setRole}
    >
      <DashboardClient access={access} />
    </AppShell>
  );
}
