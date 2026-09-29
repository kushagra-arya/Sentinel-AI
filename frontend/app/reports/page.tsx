"use client";

import Link from "next/link";
import { Download, FileBarChart2, FileText, ShieldAlert, Table2, TriangleAlert } from "lucide-react";
import { useMemo, useState } from "react";

import { AppShell, useAccessState } from "@/components/layout/app-shell";
import { cn } from "@/lib/utils";

type ReportType = {
  id: string;
  title: string;
  description: string;
  format: string;
  route: string;
  status: "Ready" | "Generated on demand" | "Future report";
};

const reports: ReportType[] = [
  {
    id: "incident",
    title: "Incident report",
    description: "Narrative, evidence chain, timeline reconstruction, and corrective actions.",
    format: "CSV + PDF",
    route: "/api/v1/incidents/{incident_id}/report",
    status: "Ready"
  },
  {
    id: "emergency-panel",
    title: "Emergency response panel",
    description: "Live actions, isolation guidance, and response priorities for open incidents.",
    format: "JSON",
    route: "/api/v1/incidents/{incident_id}/emergency-panel",
    status: "Ready"
  },
  {
    id: "daily-safety",
    title: "Daily safety summary",
    description: "Planned consolidation of alerts, incidents, and permit activity across the day.",
    format: "Planned export",
    route: "/api/v1/incidents/reports/daily-safety",
    status: "Future report"
  },
  {
    id: "risk-trend",
    title: "Risk trend report",
    description: "Trend-oriented view of compound risk movement and recurring hotspots.",
    format: "Planned export",
    route: "/api/v1/incidents/reports/risk-trend",
    status: "Future report"
  }
];

export default function ReportsPage() {
  const { role, setRole, access } = useAccessState();
  const [selected, setSelected] = useState("incident");

  const current = useMemo(() => reports.find((report) => report.id === selected) ?? reports[0], [selected]);

  return (
    <AppShell
      title="Reports"
      description="Operational exports, evidence-backed incident reports, and future reporting pipelines."
      role={role}
      access={access}
      onRoleChange={setRole}
    >
      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <section className="grid gap-4">
          <div className="grid gap-3 md:grid-cols-2">
            <StatCard label="Ready exports" value="3" icon={FileText} tone="safe" />
            <StatCard label="Planned reports" value="2" icon={FileBarChart2} tone="informational" />
          </div>

          <section className="rounded-md border border-border bg-card p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <Table2 className="h-4 w-4 text-informational" />
                  <h2 className="text-sm font-semibold">Report catalog</h2>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  Select a report type to inspect its endpoint and export status.
                </p>
              </div>
              <Link
                href="/incidents"
                className="rounded-md border border-border bg-background px-3 py-2 text-sm font-medium hover:bg-card"
              >
                Open incidents
              </Link>
            </div>

            <div className="mt-5 grid gap-3">
              {reports.map((report) => (
                <button
                  key={report.id}
                  type="button"
                  onClick={() => setSelected(report.id)}
                  className={cn(
                    "rounded-md border p-4 text-left transition-colors",
                    report.id === current.id
                      ? "border-informational bg-informational/10"
                      : "border-border bg-background hover:bg-card"
                  )}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{report.title}</span>
                        <span
                          className={cn(
                            "rounded-full px-2 py-0.5 text-xs font-medium",
                            report.status === "Ready"
                              ? "bg-safe/15 text-safe"
                              : report.status === "Generated on demand"
                                ? "bg-warning/15 text-warning"
                                : "bg-muted text-muted-foreground"
                          )}
                        >
                          {report.status}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-muted-foreground">{report.description}</p>
                    </div>
                    <Download className="h-4 w-4 text-muted-foreground" />
                  </div>
                </button>
              ))}
            </div>
          </section>
        </section>

        <aside className="grid gap-4">
          <section className="rounded-md border border-border bg-card p-5">
            <div className="flex items-start gap-3">
              <div className="rounded-md border border-border bg-background p-2">
                <ShieldAlert className="h-4 w-4 text-warning" aria-hidden="true" />
              </div>
              <div>
                <h2 className="text-sm font-semibold">Selected report</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Current export target and backend path.
                </p>
              </div>
            </div>

            <div className="mt-5 grid gap-3 text-sm">
              <MetaRow label="Title" value={current.title} />
              <MetaRow label="Format" value={current.format} />
              <MetaRow label="Endpoint" value={current.route} />
            </div>
          </section>

          <section className="rounded-md border border-border bg-card p-5">
            <div className="flex items-start gap-3">
              <div className="rounded-md border border-border bg-background p-2">
                <TriangleAlert className="h-4 w-4 text-critical" aria-hidden="true" />
              </div>
              <div>
                <h2 className="text-sm font-semibold">Operational note</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Report generation requires an incident context. Use the incident history or demo replay
                  to open one first.
                </p>
              </div>
            </div>
            <Link
              href="/timeline"
              className="mt-4 inline-flex rounded-md border border-border bg-background px-3 py-2 text-sm font-medium hover:bg-card"
            >
              Review timeline
            </Link>
          </section>
        </aside>
      </div>
    </AppShell>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  tone
}: Readonly<{
  label: string;
  value: string;
  icon: typeof FileText;
  tone: "safe" | "informational";
}>) {
  return (
    <div className="rounded-md border border-border bg-card p-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="mt-2 text-2xl font-semibold">{value}</p>
        </div>
        <div
          className={cn(
            "rounded-md border p-2",
            tone === "safe" ? "border-safe/30 bg-safe/10" : "border-informational/30 bg-informational/10"
          )}
        >
          <Icon className={cn("h-4 w-4", tone === "safe" ? "text-safe" : "text-informational")} />
        </div>
      </div>
    </div>
  );
}

function MetaRow({ label, value }: Readonly<{ label: string; value: string }>) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-md border border-border bg-background px-3 py-2.5">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground">{value}</span>
    </div>
  );
}
