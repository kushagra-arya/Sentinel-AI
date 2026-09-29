"use client";

import { Bell, Globe, Lock, Palette, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";

import { AppShell, useAccessState } from "@/components/layout/app-shell";
import { cn } from "@/lib/utils";

type ToggleItem = {
  id: string;
  title: string;
  description: string;
  enabled: boolean;
};

const initialToggles: ToggleItem[] = [
  {
    id: "compound-alerts",
    title: "Compound alert escalation",
    description: "Raise a visible escalation when multiple weak signals align into a higher-risk pattern.",
    enabled: true
  },
  {
    id: "timeline-citations",
    title: "Timeline evidence links",
    description: "Show direct evidence anchors next to each incident and alert reconstruction.",
    enabled: true
  },
  {
    id: "demo-replay",
    title: "Demo replay prompts",
    description: "Keep the guided walkthrough visible during operator demos and recorded runs.",
    enabled: true
  },
  {
    id: "email-digest",
    title: "Daily email digest",
    description: "Summarize the day’s critical alerts, reports, and unresolved follow-ups.",
    enabled: false
  }
];

export default function SettingsPage() {
  const { role, setRole, access } = useAccessState();
  const [toggles, setToggles] = useState(initialToggles);
  const [density, setDensity] = useState<"compact" | "comfortable">("comfortable");
  const [theme, setTheme] = useState<"industrial-dark" | "command-light">("industrial-dark");

  const enabledCount = useMemo(() => toggles.filter((item) => item.enabled).length, [toggles]);

  return (
    <AppShell
      title="Settings"
      description="Operational preferences, alert behavior, and workspace defaults for the command center."
      role={role}
      access={access}
      onRoleChange={setRole}
    >
      <div className="grid gap-5 xl:grid-cols-[1.3fr_0.9fr]">
        <section className="grid gap-4">
          <Panel>
            <PanelHeading
              icon={SlidersHorizontal}
              title="Alert behavior"
              subtitle="Tune how SentinelAI presents high-signal situations to operators."
            />
            <div className="mt-5 grid gap-3">
              {toggles.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() =>
                    setToggles((current) =>
                      current.map((entry) =>
                        entry.id === item.id ? { ...entry, enabled: !entry.enabled } : entry
                      )
                    )
                  }
                  className={cn(
                    "flex items-start justify-between gap-4 rounded-md border px-4 py-3 text-left transition-colors",
                    item.enabled ? "border-safe/40 bg-safe/5" : "border-border bg-background hover:bg-card"
                  )}
                >
                  <span>
                    <span className="block text-sm font-medium">{item.title}</span>
                    <span className="mt-1 block text-sm text-muted-foreground">{item.description}</span>
                  </span>
                  <span
                    className={cn(
                      "mt-1 rounded-full px-2.5 py-1 text-xs font-medium",
                      item.enabled ? "bg-safe/15 text-safe" : "bg-muted text-muted-foreground"
                    )}
                  >
                    {item.enabled ? "On" : "Off"}
                  </span>
                </button>
              ))}
            </div>
          </Panel>

          <Panel>
            <PanelHeading
              icon={Palette}
              title="Workspace appearance"
              subtitle="Choose the information density and presentation style for the dashboard."
            />
            <div className="mt-5 grid gap-3 md:grid-cols-2">
              <OptionCard
                label="Industrial Dark"
                description="High-contrast command-center layout with safe, warning, and critical signals."
                active={theme === "industrial-dark"}
                onClick={() => setTheme("industrial-dark")}
              />
              <OptionCard
                label="Command Light"
                description="Brighter presentation for review sessions and print-oriented work."
                active={theme === "command-light"}
                onClick={() => setTheme("command-light")}
              />
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-2">
              <OptionCard
                label="Comfortable density"
                description="More spacing for operators reviewing active incidents."
                active={density === "comfortable"}
                onClick={() => setDensity("comfortable")}
              />
              <OptionCard
                label="Compact density"
                description="Denser layout for monitoring multiple plants at once."
                active={density === "compact"}
                onClick={() => setDensity("compact")}
              />
            </div>
          </Panel>
        </section>

        <aside className="grid gap-4">
          <Panel>
            <PanelHeading
              icon={ShieldCheck}
              title="Access and scope"
              subtitle="Current role and assigned area used across the command center."
            />
            <div className="mt-5 grid gap-3 text-sm">
              <MetaRow label="Role" value={role.replace(/_/g, " ")} />
              <MetaRow label="Scope" value={access.assignedArea} />
              <MetaRow label="Mode" value={access.readonly ? "Read-only" : "Operational"} />
              <MetaRow label="Visible toggles" value={`${enabledCount}/${toggles.length}`} />
            </div>
          </Panel>

          <Panel>
            <PanelHeading
              icon={Bell}
              title="Notifications"
              subtitle="Signal routing for urgent response workflows."
            />
            <div className="mt-5 grid gap-3 text-sm">
              <MetaRow label="Critical alerts" value="Desktop + email" />
              <MetaRow label="Incident reports" value="Downloaded and archived" />
              <MetaRow label="Demo replay" value="Guided operator mode" />
            </div>
          </Panel>

          <Panel>
            <PanelHeading
              icon={Lock}
              title="Security"
              subtitle="Hardening defaults inherited from the backend auth model."
            />
            <div className="mt-5 grid gap-3 text-sm">
              <MetaRow label="JWT issuer" value="sentinelai-backend" />
              <MetaRow label="Session policy" value="Short-lived access tokens" />
              <MetaRow label="RBAC" value="Role-scoped navigation and APIs" />
            </div>
          </Panel>

          <Panel>
            <PanelHeading
              icon={Globe}
              title="Data freshness"
              subtitle="Local launch targets and service status used by the demo stack."
            />
            <div className="mt-5 grid gap-3 text-sm">
              <MetaRow label="Backend" value="http://127.0.0.1:8000" />
              <MetaRow label="Frontend" value="http://127.0.0.1:3000" />
              <MetaRow label="Health" value="/api/v1/health" />
            </div>
          </Panel>
        </aside>
      </div>
    </AppShell>
  );
}

function Panel({ children }: Readonly<{ children: React.ReactNode }>) {
  return <section className="rounded-md border border-border bg-card p-5">{children}</section>;
}

function PanelHeading({
  icon: Icon,
  title,
  subtitle
}: Readonly<{
  icon: typeof SlidersHorizontal;
  title: string;
  subtitle: string;
}>) {
  return (
    <div className="flex items-start gap-3">
      <div className="rounded-md border border-border bg-background p-2">
        <Icon className="h-4 w-4 text-informational" aria-hidden="true" />
      </div>
      <div>
        <h2 className="text-sm font-semibold">{title}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
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

function OptionCard({
  label,
  description,
  active,
  onClick
}: Readonly<{
  label: string;
  description: string;
  active: boolean;
  onClick: () => void;
}>) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-md border p-4 text-left transition-colors",
        active ? "border-informational bg-informational/10" : "border-border bg-background hover:bg-card"
      )}
    >
      <span className="block text-sm font-medium">{label}</span>
      <span className="mt-2 block text-sm text-muted-foreground">{description}</span>
    </button>
  );
}
