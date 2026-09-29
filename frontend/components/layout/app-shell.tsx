"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bell,
  Bot,
  Clock3,
  Flame,
  LayoutDashboard,
  Map,
  Search,
  Settings,
  ShieldAlert,
  Table2,
  UserCircle
} from "lucide-react";
import { useMemo, useState } from "react";

import { accessForRole, roleLabels, type AccessContext, type UserRole } from "@/lib/rbac";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/map", label: "Plant Map", icon: Map },
  { href: "/incidents", label: "Incidents", icon: ShieldAlert },
  { href: "/timeline", label: "Timeline", icon: Clock3 },
  { href: "/reports", label: "Reports", icon: Table2 },
  { href: "/assistant", label: "AI Assistant", icon: Bot },
  { href: "/emergency", label: "Emergency", icon: Flame },
  { href: "/settings", label: "Settings", icon: Settings }
];

export function useAccessState() {
  const [role, setRole] = useState<UserRole>("safety_officer");
  const access = useMemo(() => accessForRole(role), [role]);
  return { role, setRole, access };
}

export function AppShell({
  title,
  description,
  access,
  role,
  onRoleChange,
  children
}: Readonly<{
  title: string;
  description: string;
  access: AccessContext;
  role: UserRole;
  onRoleChange: (role: UserRole) => void;
  children: React.ReactNode;
}>) {
  const pathname = usePathname();

  return (
    <main className="min-h-screen bg-background">
      <div className="grid min-h-screen grid-cols-[240px_1fr]">
        <aside className="border-r border-border bg-card/40 px-4 py-5">
          <Link href="/" className="block border-b border-border pb-5">
            <div className="text-sm uppercase tracking-[0.18em] text-informational">SentinelAI</div>
            <div className="mt-2 text-lg font-semibold">Command Center</div>
          </Link>
          <nav className="mt-5 flex flex-col gap-1">
            {navItems.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex h-10 items-center gap-3 rounded-md px-3 text-sm text-muted-foreground",
                    active && "bg-primary/10 text-foreground"
                  )}
                >
                  <item.icon className="h-4 w-4" aria-hidden="true" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>
        <section className="flex min-w-0 flex-col">
          <header className="flex h-16 items-center justify-between border-b border-border px-6">
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                Plant
                <select className="h-9 rounded-md border border-border bg-background px-2 text-foreground">
                  <option>Refinery Unit A</option>
                  <option>Chemical Unit B</option>
                  <option>Power Block C</option>
                </select>
              </label>
              <div className="hidden h-9 min-w-[280px] items-center gap-2 rounded-md border border-border px-3 lg:flex">
                <Search className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                <input
                  aria-label="Search command center"
                  className="h-full flex-1 bg-transparent text-sm outline-none"
                  placeholder="Search alerts, assets, permits"
                />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 rounded-md border border-border px-3 py-2">
                <Bell className="h-4 w-4 text-warning" aria-hidden="true" />
                <span className="text-sm">3 active</span>
              </div>
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                Role
                <select
                  value={role}
                  onChange={(event) => onRoleChange(event.target.value as UserRole)}
                  className="h-9 rounded-md border border-border bg-background px-2 text-foreground"
                >
                  {(Object.keys(roleLabels) as UserRole[]).map((item) => (
                    <option key={item} value={item}>
                      {roleLabels[item]}
                    </option>
                  ))}
                </select>
              </label>
              <div className="flex items-center gap-2 rounded-md border border-border px-3 py-2">
                <UserCircle className="h-4 w-4 text-informational" aria-hidden="true" />
                <span className="text-sm">Ops Lead</span>
              </div>
            </div>
          </header>
          <div className="border-b border-border px-6 py-3">
            <div className="flex items-end justify-between gap-4">
              <div>
                <h1 className="text-xl font-semibold">{title}</h1>
                <p className="text-sm text-muted-foreground">{description}</p>
              </div>
              <div className="text-xs text-muted-foreground">
                Scope: {access.assignedArea} | Mode: {access.readonly ? "Read-only" : "Operational"}
              </div>
            </div>
          </div>
          <div className="min-h-0 flex-1 overflow-auto px-6 py-5">{children}</div>
        </section>
      </div>
    </main>
  );
}
