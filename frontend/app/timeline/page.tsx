"use client";

import { AppShell, useAccessState } from "@/components/layout/app-shell";
import { TimelineClient } from "@/components/timeline/timeline-client";

export default function TimelinePage() {
  const { role, setRole, access } = useAccessState();

  return (
    <AppShell
      title="Incident Timeline"
      description="Forensic reconstruction from sensor, permit, maintenance, worker, alert, and notification evidence."
      role={role}
      access={access}
      onRoleChange={setRole}
    >
      <TimelineClient access={access} />
    </AppShell>
  );
}
