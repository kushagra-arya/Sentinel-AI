import Link from "next/link";
import {
  ArrowRight,
  Activity,
  Bot,
  Clock3,
  Database,
  Flame,
  LayoutDashboard,
  Map,
  Network,
  ShieldAlert,
  ShieldCheck,
  TriangleAlert,
  Zap
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const healthItems = [
  { label: "Backend API", value: "FastAPI ready", icon: Activity },
  { label: "PostgreSQL", value: "Service-networked", icon: Database },
  { label: "ChromaDB", value: "Vector store wired", icon: Network }
];

const capabilityCards = [
  {
    title: "Compound risk engine",
    description:
      "Combines maintenance, sensor trends, worker presence, and permit context into one explainable risk picture.",
    icon: ShieldCheck,
    accent: "text-safe"
  },
  {
    title: "Evidence-first workflows",
    description:
      "Every alert, incident, and assistant answer is anchored to the events that produced it.",
    icon: TriangleAlert,
    accent: "text-warning"
  },
  {
    title: "Command-center speed",
    description:
      "A dense layout that keeps live operations, demo replay, and reporting within one focused workspace.",
    icon: Zap,
    accent: "text-informational"
  }
];

const workflow = [
  "Telemetry starts trending",
  "Maintenance context changes",
  "Worker proximity becomes relevant",
  "Compound risk crosses threshold",
  "Timeline, report, and emergency actions open instantly"
];

const views = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/map", label: "Plant Map", icon: Map },
  { href: "/timeline", label: "Timeline", icon: Clock3 },
  { href: "/incidents", label: "Incidents", icon: ShieldAlert },
  { href: "/assistant", label: "AI Assistant", icon: Bot },
  { href: "/emergency", label: "Emergency", icon: Flame }
];

export default function Home() {
  return (
    <main className="relative isolate min-h-screen overflow-hidden bg-background">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(32,201,151,0.14),transparent_32%),radial-gradient(circle_at_80%_20%,rgba(56,189,248,0.16),transparent_24%),linear-gradient(180deg,rgba(8,12,20,0.12),rgba(8,12,20,0.78))]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(148,163,184,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.06)_1px,transparent_1px)] bg-[size:96px_96px] opacity-20 [mask-image:linear-gradient(to_bottom,black,transparent_88%)]"
      />

      <section className="relative mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <div className="rounded-[2rem] border border-border/80 bg-card/70 p-6 shadow-[0_30px_80px_rgba(0,0,0,0.35)] backdrop-blur-xl lg:p-8">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border/70 pb-5">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-safe/30 bg-safe/10">
                <ShieldCheck className="h-5 w-5 text-safe" aria-hidden="true" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-informational">
                  Industrial safety intelligence
                </p>
                <h1 className="mt-1 text-2xl font-semibold text-foreground sm:text-3xl">
                  SentinelAI Command Center
                </h1>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="rounded-full border border-safe/30 bg-safe/10 px-3 py-1.5 text-sm text-safe">
                Backend ready
              </div>
              <div className="rounded-full border border-informational/30 bg-informational/10 px-3 py-1.5 text-sm text-informational">
                Demo stack online
              </div>
            </div>
          </div>

          <div className="mt-8 grid gap-8 xl:grid-cols-[1.25fr_0.75fr] xl:items-center">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-border bg-background/70 px-3 py-1.5 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Explainable compound risk detection
              </div>
              <h2 className="mt-5 max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl">
                See the dangerous combination, not just the noisy threshold.
              </h2>
              <p className="mt-5 max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
                SentinelAI fuses telemetry, maintenance state, worker proximity, permits, and incident evidence into one
                operational picture so you can act before a single alarm becomes an incident.
              </p>

              <div className="mt-8 flex flex-wrap gap-3">
                <Button asChild>
                  <Link href="/dashboard" className="inline-flex items-center gap-2">
                    Open dashboard
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </Link>
                </Button>
                <Button asChild variant="outline">
                  <Link href="/assistant" className="inline-flex items-center gap-2">
                    Explore the assistant
                    <Bot className="h-4 w-4" aria-hidden="true" />
                  </Link>
                </Button>
              </div>

              <div className="mt-8 grid gap-3 sm:grid-cols-3">
                {healthItems.map((item) => (
                  <div key={item.label} className="rounded-2xl border border-border bg-background/70 p-4">
                    <item.icon className="h-5 w-5 text-safe" aria-hidden="true" />
                    <p className="mt-3 text-xs uppercase tracking-[0.18em] text-muted-foreground">{item.label}</p>
                    <p className="mt-2 text-lg font-semibold">{item.value}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative">
              <div className="absolute inset-0 rounded-[2rem] bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.18),transparent_55%)] blur-2xl" />
              <div className="relative rounded-[2rem] border border-border bg-background/85 p-5 shadow-2xl">
                <div className="flex items-center justify-between border-b border-border pb-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Live snapshot</p>
                    <p className="mt-1 text-lg font-semibold">Compound-risk watchlist</p>
                  </div>
                  <div className="rounded-full border border-warning/30 bg-warning/10 px-3 py-1 text-xs text-warning">
                    3 active signals
                  </div>
                </div>

                <div className="mt-5 grid gap-3">
                  <SnapshotRow label="Gas trend" value="Rising" tone="warning" />
                  <SnapshotRow label="Maintenance" value="Active on Zone A" tone="critical" />
                  <SnapshotRow label="Workers nearby" value="Detected at perimeter" tone="informational" />
                  <SnapshotRow label="Risk state" value="Compound escalation ready" tone="safe" />
                </div>

                <div className="mt-5 rounded-2xl border border-border bg-card/80 p-4">
                  <div className="flex items-center gap-2">
                    <Activity className="h-4 w-4 text-informational" aria-hidden="true" />
                    <p className="text-sm font-medium">Recent evidence chain</p>
                  </div>
                  <div className="mt-4 space-y-3">
                    {[
                      "08:29 - Gas readings begin to trend upward",
                      "08:31 - Maintenance work order opens in the affected area",
                      "08:33 - Worker-location evidence enters the radius",
                      "08:44 - Compound risk crosses the alert threshold"
                    ].map((event) => (
                      <div key={event} className="flex items-start gap-3 text-sm text-muted-foreground">
                        <span className="mt-1 h-2 w-2 rounded-full bg-safe" />
                        <span>{event}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-3">
          {capabilityCards.map((card) => (
            <div key={card.title} className="rounded-3xl border border-border bg-card/75 p-5 shadow-[0_18px_48px_rgba(0,0,0,0.24)] backdrop-blur">
              <card.icon className={cn("h-5 w-5", card.accent)} aria-hidden="true" />
              <h3 className="mt-4 text-lg font-semibold">{card.title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{card.description}</p>
            </div>
          ))}
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-[2rem] border border-border bg-card/70 p-6 backdrop-blur-xl">
            <div className="flex items-center gap-2">
              <Clock3 className="h-4 w-4 text-informational" aria-hidden="true" />
              <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground">Workflow</h3>
            </div>
            <div className="mt-5 grid gap-3 lg:grid-cols-5">
              {workflow.map((step, index) => (
                <div key={step} className="rounded-2xl border border-border bg-background/70 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Step {index + 1}</p>
                  <p className="mt-3 text-sm font-medium leading-6">{step}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[2rem] border border-border bg-card/70 p-6 backdrop-blur-xl">
            <div className="flex items-center gap-2">
              <Flame className="h-4 w-4 text-warning" aria-hidden="true" />
              <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground">Direct routes</h3>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              {views.map((view) => (
                <Link
                  key={view.href}
                  href={view.href}
                  className="group flex items-center gap-3 rounded-2xl border border-border bg-background/70 p-4 transition-colors hover:border-informational/40 hover:bg-card"
                >
                  <div className="rounded-lg border border-border bg-card p-2">
                    <view.icon className="h-4 w-4 text-informational" aria-hidden="true" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{view.label}</p>
                    <p className="text-xs text-muted-foreground">Open module</p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

function SnapshotRow({
  label,
  value,
  tone
}: Readonly<{
  label: string;
  value: string;
  tone: "safe" | "warning" | "critical" | "informational";
}>) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-border bg-card/80 px-4 py-3">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span
        className={cn(
          "rounded-full px-3 py-1 text-xs font-medium",
          tone === "safe" && "bg-safe/10 text-safe",
          tone === "warning" && "bg-warning/10 text-warning",
          tone === "critical" && "bg-critical/10 text-critical",
          tone === "informational" && "bg-informational/10 text-informational"
        )}
      >
        {value}
      </span>
    </div>
  );
}
