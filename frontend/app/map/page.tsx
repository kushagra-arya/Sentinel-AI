"use client";

import { AppShell, useAccessState } from "@/components/layout/app-shell";
import { PlantMapClient } from "@/components/map/plant-map-client";

export default function MapPage() {
  const { role, setRole, access } = useAccessState();

  return (
    <AppShell
      title="Plant Map"
      description="Evidence-positioned markers, permit zones, hazard overlays, and computed risk heatmap."
      role={role}
      access={access}
      onRoleChange={setRole}
    >
      <PlantMapClient access={access} />
    </AppShell>
  );
}
