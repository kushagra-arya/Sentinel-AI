"use client";

import { motion } from "framer-motion";
import { AlertTriangle, ShieldAlert } from "lucide-react";

import type { DashboardEvent } from "@/lib/dashboard-types";
import { cn } from "@/lib/utils";

export function AlertsList({
  activeAlerts,
  criticalAlerts,
  events
}: Readonly<{
  activeAlerts: number;
  criticalAlerts: number;
  events: DashboardEvent[];
}>) {
  const alertEvents = events.filter((event) => event.event_type === "alert").slice(0, 5);

  return (
    <section className="rounded-md border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <ShieldAlert className="h-4 w-4 text-warning" />
          Active Alerts
        </h2>
        <div className="text-sm text-muted-foreground">
          {activeAlerts} active | <span className="text-critical">{criticalAlerts} critical</span>
        </div>
      </div>
      <div className="divide-y divide-border">
        {(alertEvents.length ? alertEvents : fallbackAlerts).map((event) => (
          <motion.a
            key={`${event.title}-${event.occurred_at}`}
            href="/timeline"
            initial={{ backgroundColor: "rgba(245, 158, 11, 0.08)" }}
            animate={{ backgroundColor: "rgba(0, 0, 0, 0)" }}
            transition={{ duration: 0.45 }}
            className="grid grid-cols-[24px_1fr_auto] items-center gap-3 px-4 py-3 text-sm hover:bg-background"
          >
            <AlertTriangle className={cn("h-4 w-4", severityColor(event.severity))} />
            <span>
              <span className="block font-medium">{event.title}</span>
              <span className="text-muted-foreground">{event.event_type}</span>
            </span>
            <time className="text-xs text-muted-foreground">
              {new Date(event.occurred_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit"
              })}
            </time>
          </motion.a>
        ))}
      </div>
    </section>
  );
}

const fallbackAlerts: DashboardEvent[] = [
  {
    event_type: "alert",
    title: "High compound gas risk",
    severity: "high",
    occurred_at: "2026-07-07T10:15:00.000Z"
  }
];

function severityColor(severity: string) {
  if (severity === "critical") {
    return "text-critical";
  }
  if (severity === "high") {
    return "text-warning";
  }
  return "text-informational";
}
