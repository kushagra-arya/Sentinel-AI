"use client";

import { AssistantClient } from "@/components/assistant/assistant-client";
import { AppShell, useAccessState } from "@/components/layout/app-shell";

export default function AssistantPage() {
  const { role, setRole, access } = useAccessState();

  return (
    <AppShell
      title="AI Assistant"
      description="Retrieval-grounded safety guidance with explicit citations and no-source handling."
      role={role}
      access={access}
      onRoleChange={setRole}
    >
      <AssistantClient access={access} />
    </AppShell>
  );
}
