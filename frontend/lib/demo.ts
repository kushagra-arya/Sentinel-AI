import { apiGet } from "@/lib/api";

export type DemoStatus = {
  current_step: number;
  current_step_name: string;
  plant_id: string | null;
  alert_id: string | null;
  incident_id: string | null;
  demo_user_email: string;
  demo_user_password: string;
};

export async function getDemoStatus(): Promise<DemoStatus> {
  return apiGet<DemoStatus>("/demo/replay/status");
}
