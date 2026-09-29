"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, PhoneCall, ShieldAlert, Users, Wrench } from "lucide-react";
import type { ComponentType, ReactNode } from "react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { apiGet } from "@/lib/api";
import { getDemoStatus } from "@/lib/demo";
import { canMutate, type AccessContext } from "@/lib/rbac";

type WorkerPresence = {
  worker_id: string;
  badge_id: string | null;
  full_name: string | null;
  zone: string;
  observed_at: string;
};
type NearbyEquipment = {
  equipment_id: string;
  asset_tag: string;
  name: string;
  equipment_type: string;
  zone: string;
  status: string;
};
type RoleAction = { role: string; action: string; priority: number };
type EmergencyContact = { role: string; name: string; channel: string };
type EmergencyPanelState = {
  incident_id: string;
  affected_area: string;
  risk_level: "low" | "medium" | "high" | "critical";
  triggering_rules: string[];
  workers_present: WorkerPresence[];
  nearby_equipment: NearbyEquipment[];
  nearest_exit: string;
  emergency_contacts: EmergencyContact[];
  recommended_actions: RoleAction[];
};
type IncidentReport = {
  incident_id: string;
  risk_type: string;
  affected_zone: string;
  evidence_summary: { entity_type: string; entity_id: string; description: string; value: string | null }[];
};
type ExportResponse = { filename: string; media_type: string; content_base64: string };

const fallbackPanel: EmergencyPanelState = {
  incident_id: "demo-incident",
  affected_area: "Zone A",
  risk_level: "high",
  triggering_rules: ["gas_increasing_maintenance_workers"],
  workers_present: [
    {
      worker_id: "worker-17",
      badge_id: "BW-17",
      full_name: "Field Operator",
      zone: "Zone A",
      observed_at: "2026-07-07T10:16:00.000Z"
    }
  ],
  nearby_equipment: [
    {
      equipment_id: "pump-17",
      asset_tag: "P-17",
      name: "Pump P-17",
      equipment_type: "pump",
      zone: "Zone A",
      status: "active"
    }
  ],
  nearest_exit: "North muster exit A1",
  emergency_contacts: [
    { role: "Incident Commander", name: "Shift Safety Lead", channel: "radio-1" },
    { role: "Medical", name: "On-site medical room", channel: "extension-222" }
  ],
  recommended_actions: [
    { role: "Supervisor", action: "Move workers out of the affected zone immediately.", priority: 1 },
    { role: "Safety Officer", action: "Pause maintenance and verify gas trend with portable meter.", priority: 2 },
    { role: "Maintenance Lead", action: "Confirm isolation and remove ignition sources.", priority: 3 }
  ]
};

const fallbackReport: IncidentReport = {
  incident_id: "demo-incident",
  risk_type: "Gas rise during maintenance with workers nearby",
  affected_zone: "Zone A",
  evidence_summary: [
    { entity_type: "sensor_reading", entity_id: "sr-42", description: "Gas reading quality good", value: "42" },
    { entity_type: "maintenance_activity", entity_id: "wo-17", description: "inspection maintenance", value: "WO-17" }
  ]
};

export function EmergencyPanelClient({ access }: Readonly<{ access: AccessContext }>) {
  const [incidentId, setIncidentId] = useState("demo-incident");
  const demoQuery = useQuery({
    queryKey: ["demo-status"],
    queryFn: getDemoStatus,
    refetchInterval: 2_000,
    staleTime: 1_000
  });
  const activeIncidentId = incidentId === "demo-incident"
    ? demoQuery.data?.incident_id ?? incidentId
    : incidentId;
  const panelQuery = useQuery({
    queryKey: ["emergency-panel", activeIncidentId],
    queryFn: () => apiGet<EmergencyPanelState>(`/incidents/${activeIncidentId}/emergency-panel`),
    enabled: activeIncidentId !== "demo-incident",
    refetchInterval: 5_000
  });
  const reportQuery = useQuery({
    queryKey: ["incident-report", activeIncidentId],
    queryFn: () => apiGet<IncidentReport>(`/incidents/${activeIncidentId}/report`),
    enabled: activeIncidentId !== "demo-incident",
    staleTime: 10_000
  });

  const panel = panelQuery.data ?? fallbackPanel;
  const report = reportQuery.data ?? fallbackReport;

  async function exportReport(format: "csv" | "pdf") {
    if (activeIncidentId === "demo-incident") {
      return;
    }
    const response = await apiGet<ExportResponse>(`/incidents/${activeIncidentId}/report.${format}`);
    const link = document.createElement("a");
    link.href = `data:${response.media_type};base64,${response.content_base64}`;
    link.download = response.filename;
    link.click();
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
      <section className="grid gap-4">
        <div className="rounded-md border border-critical/60 bg-critical/5 p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.18em] text-critical">Live Incident</p>
              <h2 className="mt-2 text-3xl font-semibold">{panel.affected_area}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{report.risk_type}</p>
            </div>
            <div className="rounded-md border border-critical px-3 py-2 text-sm font-semibold uppercase text-critical">
              {panel.risk_level}
            </div>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <InfoBlock icon={Users} title="Workers Present">
            {panel.workers_present.map((worker) => (
              <div key={worker.worker_id} className="text-sm">
                <span className="block font-medium">{worker.full_name ?? worker.worker_id}</span>
                <span className="text-muted-foreground">{worker.badge_id ?? "No badge"} | {worker.zone}</span>
              </div>
            ))}
          </InfoBlock>
          <InfoBlock icon={Wrench} title="Nearby Equipment">
            {panel.nearby_equipment.map((item) => (
              <div key={item.equipment_id} className="text-sm">
                <span className="block font-medium">{item.name}</span>
                <span className="text-muted-foreground">{item.asset_tag} | {item.status}</span>
              </div>
            ))}
          </InfoBlock>
          <InfoBlock icon={PhoneCall} title="Emergency Contacts">
            {panel.emergency_contacts.map((contact) => (
              <div key={contact.channel} className="text-sm">
                <span className="block font-medium">{contact.role}</span>
                <span className="text-muted-foreground">{contact.name} | {contact.channel}</span>
              </div>
            ))}
          </InfoBlock>
        </div>

        <section className="rounded-md border border-border bg-card p-4">
          <h2 className="text-sm font-semibold">Role-Specific Actions</h2>
          <div className="mt-4 grid gap-3">
            {panel.recommended_actions
              .sort((left, right) => left.priority - right.priority)
              .map((action) => (
                <div key={`${action.role}-${action.priority}`} className="rounded-md border border-border p-3">
                  <span className="text-sm font-semibold">{action.role}</span>
                  <p className="mt-1 text-sm text-muted-foreground">{action.action}</p>
                </div>
              ))}
          </div>
        </section>
      </section>

      <aside className="grid content-start gap-4">
        <section className="rounded-md border border-border bg-card p-4">
          <h2 className="flex items-center gap-2 text-sm font-semibold">
            <ShieldAlert className="h-4 w-4 text-warning" />
            Incident Report
          </h2>
          <label className="mt-4 block text-sm text-muted-foreground">
            Incident ID
            <input
              value={incidentId}
              onChange={(event) => setIncidentId(event.target.value)}
              className="mt-2 h-10 w-full rounded-md border border-border bg-background px-3 text-foreground"
            />
          </label>
          <div className="mt-4 text-sm text-muted-foreground">
            Nearest exit: <span className="text-foreground">{panel.nearest_exit}</span>
          </div>
          <div className="mt-4 grid gap-2">
            <Button onClick={() => void exportReport("pdf")} disabled={!canMutate(access)}>
              <Download className="mr-2 h-4 w-4" />
              Export PDF
            </Button>
            <Button variant="outline" onClick={() => void exportReport("csv")} disabled={!canMutate(access)}>
              <Download className="mr-2 h-4 w-4" />
              Export CSV
            </Button>
          </div>
        </section>

        <section className="rounded-md border border-border bg-card p-4">
          <h2 className="text-sm font-semibold">Evidence Summary</h2>
          <div className="mt-4 space-y-3">
            {report.evidence_summary.map((item) => (
              <div
                key={`${item.entity_type}-${item.entity_id}`}
                className="rounded-md border border-border p-3 text-sm"
              >
                <span className="block font-medium">{item.entity_type}</span>
                <span className="block text-muted-foreground">{item.entity_id}</span>
                <span className="mt-1 block">{item.description}</span>
              </div>
            ))}
          </div>
        </section>
      </aside>
    </div>
  );
}

function InfoBlock({
  icon: Icon,
  title,
  children
}: Readonly<{
  icon: ComponentType<{ className?: string }>;
  title: string;
  children: ReactNode;
}>) {
  return (
    <section className="rounded-md border border-border bg-card p-4">
      <h2 className="flex items-center gap-2 text-sm font-semibold">
        <Icon className="h-4 w-4 text-informational" />
        {title}
      </h2>
      <div className="mt-4 space-y-3">{children}</div>
    </section>
  );
}
