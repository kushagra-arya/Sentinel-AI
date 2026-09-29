"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Clock3, FileText, Wrench } from "lucide-react";
import { useMemo, useState } from "react";

import { apiGet } from "@/lib/api";
import { getDemoStatus } from "@/lib/demo";
import { canSeeArea, type AccessContext } from "@/lib/rbac";
import { cn } from "@/lib/utils";

type TimelineEntry = {
  occurred_at: string;
  event_type: string;
  title: string;
  description: string;
  evidence: {
    entity_type: string;
    entity_id: string;
    api_path: string;
  };
};

type TimelineResponse = {
  subject_type: string;
  subject_id: string;
  entries: TimelineEntry[];
};

const fallbackTimeline: TimelineResponse = {
  subject_type: "incident",
  subject_id: "demo-incident",
  entries: [
    {
      occurred_at: "2026-07-07T10:00:00.000Z",
      event_type: "sensor_reading",
      title: "Gas begins increasing",
      description: "Gas reading trend begins moving upward in Zone A.",
      evidence: { entity_type: "sensor_reading", entity_id: "sr-01", api_path: "/api/v1/sensor-readings/sr-01" }
    },
    {
      occurred_at: "2026-07-07T10:05:00.000Z",
      event_type: "maintenance_started",
      title: "Maintenance starts",
      description: "Maintenance work order WO-101 starts in Zone A.",
      evidence: { entity_type: "maintenance_activity", entity_id: "wo-101", api_path: "/api/v1/maintenance/wo-101" }
    },
    {
      occurred_at: "2026-07-07T10:10:00.000Z",
      event_type: "worker_entered_area",
      title: "Workers enter area",
      description: "Two workers are observed inside the affected zone.",
      evidence: {
        entity_type: "worker_location_event",
        entity_id: "wl-22",
        api_path: "/api/v1/worker-location-events/wl-22"
      }
    },
    {
      occurred_at: "2026-07-07T10:15:00.000Z",
      event_type: "compound_alert",
      title: "Compound risk alert raised",
      description: "Rule gas_increasing_maintenance_workers raises a high-risk alert.",
      evidence: { entity_type: "alert", entity_id: "alert-01", api_path: "/api/v1/alerts/alert-01" }
    },
    {
      occurred_at: "2026-07-07T10:16:00.000Z",
      event_type: "notification_sent",
      title: "Supervisor notified",
      description: "Supervisor receives in-app and email notification.",
      evidence: { entity_type: "notification", entity_id: "notif-01", api_path: "/api/v1/notifications/notif-01" }
    }
  ]
};

const icons = {
  sensor_reading: Clock3,
  maintenance_started: Wrench,
  worker_entered_area: FileText,
  compound_alert: AlertTriangle,
  notification_sent: FileText
};

export function TimelineClient({ access }: Readonly<{ access: AccessContext }>) {
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
  const { data } = useQuery({
    queryKey: ["timeline", activeIncidentId],
    queryFn: () => apiGet<TimelineResponse>(`/timeline/incidents/${activeIncidentId}`),
    enabled: activeIncidentId !== "demo-incident"
  });
  const timeline = data ?? fallbackTimeline;

  const visibleEntries = useMemo(
    () => timeline.entries.filter(() => canSeeArea(access, "Zone A")),
    [access, timeline.entries]
  );

  return (
    <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
      <aside className="rounded-md border border-border bg-card p-4">
        <h2 className="text-sm font-semibold">Incident Lookup</h2>
        <label className="mt-4 block text-sm text-muted-foreground">
          Incident ID
          <input
            value={incidentId}
            onChange={(event) => setIncidentId(event.target.value)}
            className="mt-2 h-10 w-full rounded-md border border-border bg-background px-3 text-foreground"
          />
        </label>
        <div className="mt-4 rounded-md border border-border p-3 text-sm text-muted-foreground">
          Timeline is generated from evidence links only. Each entry below links to its source record.
        </div>
      </aside>

      <section className="rounded-md border border-border bg-card">
        <div className="border-b border-border px-5 py-4">
          <h2 className="text-base font-semibold">Causal Sequence</h2>
          <p className="text-sm text-muted-foreground">
            {timeline.subject_type} | {timeline.subject_id}
          </p>
        </div>
        <div className="divide-y divide-border">
          {visibleEntries.map((entry, index) => {
            const Icon = icons[entry.event_type as keyof typeof icons] ?? FileText;
            return (
              <a
                key={`${entry.evidence.entity_id}-${index}`}
                href={entry.evidence.api_path}
                className="grid grid-cols-[120px_32px_1fr] gap-4 px-5 py-4 hover:bg-background"
              >
                <time className="text-sm text-muted-foreground">
                  {new Date(entry.occurred_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit"
                  })}
                </time>
                <span
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-md border",
                    entry.event_type === "compound_alert"
                      ? "border-critical text-critical"
                      : "border-border text-informational"
                  )}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                </span>
                <div>
                  <h3 className="text-sm font-semibold">{entry.title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{entry.description}</p>
                  <p className="mt-2 text-xs text-informational">
                    {entry.evidence.entity_type}: {entry.evidence.entity_id}
                  </p>
                </div>
              </a>
            );
          })}
        </div>
      </section>
    </div>
  );
}
