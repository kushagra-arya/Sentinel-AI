"use client";

import { Search, SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";

import { canSeeArea, type AccessContext } from "@/lib/rbac";

type IncidentRecord = {
  id: string;
  date: string;
  area: string;
  equipment: string;
  riskType: string;
  severity: "low" | "medium" | "high" | "critical";
  category: "Past Incident" | "Near Miss" | "Alert" | "Sensor Data" | "Report" | "Corrective Action";
  status: string;
  summary: string;
};

const records: IncidentRecord[] = [
  {
    id: "INC-1042",
    date: "2026-07-07",
    area: "Zone A",
    equipment: "Compressor C-12",
    riskType: "Gas + Maintenance + Workers",
    severity: "high",
    category: "Past Incident",
    status: "Investigating",
    summary: "Compound gas risk raised before threshold alarm."
  },
  {
    id: "NM-220",
    date: "2026-07-06",
    area: "Zone B",
    equipment: "Ventilation Stack V-2",
    riskType: "Confined Space Ventilation",
    severity: "critical",
    category: "Near Miss",
    status: "Corrective Action Open",
    summary: "Ventilation recovered before entry authorization."
  },
  {
    id: "AL-771",
    date: "2026-07-05",
    area: "Zone A",
    equipment: "Pressure Vessel P-4",
    riskType: "Temperature + Pressure",
    severity: "medium",
    category: "Alert",
    status: "Resolved",
    summary: "Pressure trend stabilized after load reduction."
  },
  {
    id: "SD-443",
    date: "2026-07-04",
    area: "Zone C",
    equipment: "Gas Sensor G-8",
    riskType: "Sensor Drift",
    severity: "low",
    category: "Sensor Data",
    status: "Reviewed",
    summary: "Telemetry quality degraded and recovered after calibration."
  },
  {
    id: "RPT-91",
    date: "2026-07-03",
    area: "Zone A",
    equipment: "Permit System",
    riskType: "Permit Compliance",
    severity: "medium",
    category: "Report",
    status: "Filed",
    summary: "Daily permit summary flagged two delayed closures."
  },
  {
    id: "CA-18",
    date: "2026-07-02",
    area: "Zone B",
    equipment: "Ventilation Stack V-2",
    riskType: "Ventilation Procedure",
    severity: "high",
    category: "Corrective Action",
    status: "Owner Assigned",
    summary: "Add pre-entry ventilation verification checklist."
  }
];

const severities = ["all", "low", "medium", "high", "critical"];

export function IncidentHistoryClient({ access }: Readonly<{ access: AccessContext }>) {
  const [query, setQuery] = useState("");
  const [area, setArea] = useState("all");
  const [equipment, setEquipment] = useState("all");
  const [severity, setSeverity] = useState("all");
  const [date, setDate] = useState("");

  const areas = ["all", ...Array.from(new Set(records.map((record) => record.area)))];
  const equipmentOptions = ["all", ...Array.from(new Set(records.map((record) => record.equipment)))];

  const filtered = useMemo(() => {
    return records.filter((record) => {
      const text = `${record.id} ${record.riskType} ${record.summary}`.toLowerCase();
      return (
        canSeeArea(access, record.area) &&
        (query === "" || text.includes(query.toLowerCase())) &&
        (area === "all" || record.area === area) &&
        (equipment === "all" || record.equipment === equipment) &&
        (severity === "all" || record.severity === severity) &&
        (date === "" || record.date === date)
      );
    });
  }, [access, area, date, equipment, query, severity]);

  return (
    <div className="grid gap-4">
      <section className="rounded-md border border-border bg-card p-4">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-informational" />
          <h2 className="text-sm font-semibold">Filters</h2>
        </div>
        <div className="mt-4 grid gap-3 lg:grid-cols-[1.4fr_repeat(4,1fr)]">
          <label className="relative text-sm text-muted-foreground">
            Search
            <Search className="absolute bottom-3 left-3 h-4 w-4 text-muted-foreground" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="mt-2 h-10 w-full rounded-md border border-border bg-background pl-9 pr-3 text-foreground"
            />
          </label>
          <Filter label="Area" value={area} onChange={setArea} options={areas} />
          <Filter label="Equipment" value={equipment} onChange={setEquipment} options={equipmentOptions} />
          <Filter label="Severity" value={severity} onChange={setSeverity} options={severities} />
          <label className="text-sm text-muted-foreground">
            Date
            <input
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
              className="mt-2 h-10 w-full rounded-md border border-border bg-background px-3 text-foreground"
            />
          </label>
        </div>
      </section>

      <section className="overflow-hidden rounded-md border border-border bg-card">
        <div
          className={[
            "grid grid-cols-[110px_130px_1fr_150px_120px_140px] border-b border-border",
            "px-4 py-3 text-xs uppercase tracking-[0.12em] text-muted-foreground"
          ].join(" ")}
        >
          <span>Date</span>
          <span>Category</span>
          <span>Risk / Equipment</span>
          <span>Area</span>
          <span>Severity</span>
          <span>Status</span>
        </div>
        <div className="divide-y divide-border">
          {filtered.map((record) => (
            <a
              key={record.id}
              href={`/timeline?subject=${record.id}`}
              className="grid grid-cols-[110px_130px_1fr_150px_120px_140px] px-4 py-4 text-sm hover:bg-background"
            >
              <span className="text-muted-foreground">{record.date}</span>
              <span>{record.category}</span>
              <span>
                <span className="block font-medium">{record.riskType}</span>
                <span className="text-muted-foreground">{record.equipment} | {record.summary}</span>
              </span>
              <span>{record.area}</span>
              <span className={severityClass(record.severity)}>{record.severity}</span>
              <span className="text-muted-foreground">{record.status}</span>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}

function Filter({
  label,
  value,
  onChange,
  options
}: Readonly<{
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
}>) {
  return (
    <label className="text-sm text-muted-foreground">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 h-10 w-full rounded-md border border-border bg-background px-3 text-foreground"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function severityClass(severity: IncidentRecord["severity"]) {
  return {
    low: "text-safe",
    medium: "text-informational",
    high: "text-warning",
    critical: "text-critical"
  }[severity];
}
