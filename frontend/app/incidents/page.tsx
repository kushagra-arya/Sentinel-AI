"use client";

import { AppShell, useAccessState } from "@/components/layout/app-shell";
import { IncidentHistoryClient } from "@/components/incidents/incident-history-client";

export default function IncidentsPage() {
  const { role, setRole, access } = useAccessState();

  return (
    <AppShell
      title="Incident History"
      description="Searchable record of incidents, near misses, alerts, sensor data, reports, and corrective actions."
      role={role}
      access={access}
      onRoleChange={setRole}
    >
      <IncidentHistoryClient access={access} />
    </AppShell>
  );
}
