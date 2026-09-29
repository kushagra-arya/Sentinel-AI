"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertOctagon, CheckCircle2, Flame, Siren, Users } from "lucide-react";
import type { ComponentType } from "react";
import { useMemo } from "react";

import { AlertsList } from "@/components/alerts/alerts-list";
import { ChartPanel } from "@/components/charts/chart-panel";
import { RiskScore } from "@/components/risk-score/risk-score";
import { apiGet } from "@/lib/api";
import type { DashboardSummary, RiskPredictionResponse } from "@/lib/dashboard-types";
import { getDemoStatus } from "@/lib/demo";
import { type AccessContext } from "@/lib/rbac";

const plantId = "demo-plant";

const fallbackSummary: DashboardSummary = {
  plant_id: plantId,
  current_risk_score: 0.82,
  current_risk_level: "high",
  active_alerts: 7,
  critical_alerts: 2,
  worker_count: 42,
  active_permits: 6,
  maintenance_activities: 3,
  gas_status: { status: "rising", value: 44, unit: "ppm", observed_at: "2026-07-07T10:15:00.000Z" },
  temperature_status: {
    status: "stable",
    value: 62,
    unit: "celsius",
    observed_at: "2026-07-07T10:15:00.000Z"
  },
  equipment_health: { status: "degraded", value: 31, unit: "healthy_assets", observed_at: null },
  recent_incidents: 2,
  live_event_feed: [
    {
      event_type: "alert",
      title: "High compound gas risk",
      severity: "high",
      occurred_at: "2026-07-07T10:15:00.000Z"
    },
    {
      event_type: "incident",
      title: "Near miss opened",
      severity: "medium",
      occurred_at: "2026-07-07T09:42:00.000Z"
    }
  ]
};

const fallbackPredictions: RiskPredictionResponse = {
  plant_id: plantId,
  predictions: [
    {
      signal: "gas",
      predicted_value: 53,
      horizon_minutes: 30,
      trend: "increasing",
      risk_level: "high",
      minutes_to_high_risk: 18
    },
    {
      signal: "temperature",
      predicted_value: 68,
      horizon_minutes: 30,
      trend: "flat",
      risk_level: "low",
      minutes_to_high_risk: null
    },
    {
      signal: "pressure",
      predicted_value: 114,
      horizon_minutes: 30,
      trend: "increasing",
      risk_level: "low",
      minutes_to_high_risk: null
    }
  ]
};

export function DashboardClient({ access }: Readonly<{ access: AccessContext }>) {
  const demoQuery = useQuery({
    queryKey: ["demo-status"],
    queryFn: getDemoStatus,
    refetchInterval: 2_000,
    staleTime: 1_000
  });
  const activePlantId = demoQuery.data?.plant_id ?? plantId;
  const dashboardQuery = useQuery({
    queryKey: ["dashboard-summary", activePlantId],
    queryFn: () => apiGet<DashboardSummary>(`/dashboard/summary?plant_id=${activePlantId}`),
    enabled: Boolean(activePlantId),
    refetchInterval: 5_000,
    staleTime: 3_000
  });

  const predictionsQuery = useQuery({
    queryKey: ["risk-predictions", activePlantId],
    queryFn: () => apiGet<RiskPredictionResponse>(`/risk/predictions?plant_id=${activePlantId}`),
    enabled: Boolean(activePlantId),
    refetchInterval: 30_000,
    staleTime: 20_000
  });

  const summary = dashboardQuery.data ?? fallbackSummary;
  const predictions = predictionsQuery.data?.predictions ?? fallbackPredictions.predictions;

  const trendOption = useMemo(
    () => ({
      color: ["#38bdf8", "#f59e0b", "#ef4444"],
      tooltip: { trigger: "axis" },
      grid: { left: 42, right: 18, top: 20, bottom: 32 },
      xAxis: { type: "category", data: ["-25m", "-20m", "-15m", "-10m", "-5m", "now", "+30m"] },
      yAxis: { type: "value", splitLine: { lineStyle: { color: "#1e293b" } } },
      series: [
        {
          name: "Gas",
          type: "line",
          smooth: false,
          data: [22, 24, 28, 33, 39, summary.gas_status.value ?? 44, predictions[0]?.predicted_value ?? 44]
        },
        {
          name: "Temperature",
          type: "line",
          smooth: false,
          data: [58, 59, 60, 61, 61, summary.temperature_status.value ?? 62, predictions[1]?.predicted_value ?? 62]
        }
      ]
    }),
    [predictions, summary.gas_status.value, summary.temperature_status.value]
  );

  const distributionOption = useMemo(
    () => ({
      color: ["#22c55e", "#38bdf8", "#f59e0b", "#ef4444"],
      tooltip: { trigger: "item" },
      legend: { bottom: 0, textStyle: { color: "#94a3b8" } },
      series: [
        {
          type: "pie",
          radius: ["45%", "68%"],
          data: [
            { value: 18, name: "Low" },
            { value: 9, name: "Medium" },
            { value: summary.active_alerts, name: "High" },
            { value: summary.critical_alerts, name: "Critical" }
          ]
        }
      ]
    }),
    [summary.active_alerts, summary.critical_alerts]
  );

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
      <section className="grid min-w-0 gap-4">
        <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
          <RiskScore
            score={summary.current_risk_score}
            level={summary.current_risk_level}
            predictions={predictions}
          />
          <div className="grid gap-4 md:grid-cols-4">
            <Metric label="Active Alerts" value={summary.active_alerts} icon={AlertOctagon} tone="warning" />
            <Metric label="Critical Alerts" value={summary.critical_alerts} icon={Siren} tone="critical" />
            <Metric label="Workers" value={summary.worker_count} icon={Users} tone="informational" />
            <Metric label="Permits" value={summary.active_permits} icon={CheckCircle2} tone="safe" />
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
          <AlertsList
            activeAlerts={summary.active_alerts}
            criticalAlerts={summary.critical_alerts}
            events={summary.live_event_feed}
          />
          <section className="rounded-md border border-border bg-card p-4">
            <h2 className="text-sm font-semibold">Telemetry Status</h2>
            <div className="mt-4 grid gap-3">
              <StatusRow label="Gas" value={summary.gas_status.value} unit={summary.gas_status.unit} />
              <StatusRow
                label="Temperature"
                value={summary.temperature_status.value}
                unit={summary.temperature_status.unit}
              />
              <StatusRow
                label="Equipment"
                value={summary.equipment_health.value}
                unit={summary.equipment_health.unit}
              />
            </div>
          </section>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <ChartPanel
            title="Gas and Temperature Trend"
            description="Current telemetry and thirty-minute forward signal."
            option={trendOption}
          />
          <ChartPanel
            title="Alert Risk Distribution"
            description="Severity distribution across active operational risk."
            option={distributionOption}
          />
        </div>

        <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
          <HeatmapPreview />
          <TimelinePreview events={summary.live_event_feed} />
        </div>
      </section>

      <RightPanel access={access} events={summary.live_event_feed} />
    </div>
  );
}

function Metric({
  label,
  value,
  icon: Icon,
  tone
}: Readonly<{
  label: string;
  value: number;
  icon: ComponentType<{ className?: string }>;
  tone: "safe" | "warning" | "critical" | "informational";
}>) {
  const toneClass = {
    safe: "text-safe",
    warning: "text-warning",
    critical: "text-critical",
    informational: "text-informational"
  }[tone];
  return (
    <section className="rounded-md border border-border bg-card p-4">
      <Icon className={`h-4 w-4 ${toneClass}`} aria-hidden="true" />
      <p className="mt-4 text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-3xl font-semibold">{value}</p>
    </section>
  );
}

function StatusRow({ label, value, unit }: Readonly<{ label: string; value: number | null; unit: string | null }>) {
  return (
    <div className="flex items-center justify-between rounded-md border border-border px-3 py-2">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-semibold">
        {value ?? "n/a"} {unit ?? ""}
      </span>
    </div>
  );
}

function HeatmapPreview() {
  return (
    <section className="rounded-md border border-border bg-card p-4">
      <h2 className="text-sm font-semibold">Risk Heatmap</h2>
      <div className="mt-4 grid h-56 grid-cols-6 gap-1">
        {Array.from({ length: 36 }).map((_, index) => {
          const intensity =
            index === 14 || index === 15
              ? "bg-critical/60"
              : index > 8 && index < 22
                ? "bg-warning/35"
                : "bg-safe/15";
          return <div key={index} className={`rounded-sm border border-border ${intensity}`} />;
        })}
      </div>
    </section>
  );
}

function TimelinePreview({ events }: Readonly<{ events: DashboardSummary["live_event_feed"] }>) {
  return (
    <section className="rounded-md border border-border bg-card">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold">Timeline</h2>
      </div>
      <div className="divide-y divide-border">
        {events.slice(0, 4).map((event) => (
          <a
            key={`${event.title}-${event.occurred_at}`}
            href="/timeline"
            className="block px-4 py-3 hover:bg-background"
          >
            <span className="block text-sm font-medium">{event.title}</span>
            <span className="text-xs text-muted-foreground">
              {event.event_type} | {new Date(event.occurred_at).toLocaleString()}
            </span>
          </a>
        ))}
      </div>
    </section>
  );
}

function RightPanel({
  access,
  events
}: Readonly<{
  access: AccessContext;
  events: DashboardSummary["live_event_feed"];
}>) {
  return (
    <aside className="grid content-start gap-4">
      <section className="rounded-md border border-border bg-card p-4">
        <h2 className="text-sm font-semibold">Recommendations</h2>
        <div className="mt-4 space-y-3 text-sm text-muted-foreground">
          <p>Verify gas trend in Zone A and confirm active maintenance isolation.</p>
          <p>Keep supervisors assigned to affected workers until risk returns below medium.</p>
        </div>
      </section>
      <section className="rounded-md border border-border bg-card p-4">
        <h2 className="text-sm font-semibold">Recent Events</h2>
        <div className="mt-3 space-y-3">
          {events.map((event) => (
            <div key={`${event.title}-${event.occurred_at}`} className="text-sm">
              <span className="block">{event.title}</span>
              <span className="text-xs text-muted-foreground">{event.severity}</span>
            </div>
          ))}
        </div>
      </section>
      <section className="rounded-md border border-critical/50 bg-critical/5 p-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-critical">
          <Flame className="h-4 w-4" />
          Emergency Actions
        </h2>
        <div className="mt-4 grid gap-2">
          {["Evacuate Zone", "Notify Supervisor", "Open Incident"].map((action) => (
            <button
              key={action}
              disabled={access.readonly}
              className={[
                "h-10 rounded-md border border-critical/40 px-3 text-left text-sm",
                "text-foreground disabled:opacity-50"
              ].join(" ")}
            >
              {action}
            </button>
          ))}
        </div>
      </section>
    </aside>
  );
}
