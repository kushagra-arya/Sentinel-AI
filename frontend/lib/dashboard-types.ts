export type RiskLevel = "low" | "medium" | "high" | "critical";

export type StatusSummary = {
  status: string;
  value: number | null;
  unit: string | null;
  observed_at: string | null;
};

export type DashboardEvent = {
  event_type: string;
  title: string;
  severity: string;
  occurred_at: string;
};

export type DashboardSummary = {
  plant_id: string;
  current_risk_score: number;
  current_risk_level: RiskLevel;
  active_alerts: number;
  critical_alerts: number;
  worker_count: number;
  active_permits: number;
  maintenance_activities: number;
  gas_status: StatusSummary;
  temperature_status: StatusSummary;
  equipment_health: StatusSummary;
  recent_incidents: number;
  live_event_feed: DashboardEvent[];
};

export type RiskPrediction = {
  signal: string;
  predicted_value: number;
  horizon_minutes: number;
  trend: string;
  risk_level: RiskLevel;
  minutes_to_high_risk: number | null;
};

export type RiskPredictionResponse = {
  plant_id: string;
  predictions: RiskPrediction[];
};
