/**
 * Environment & Weather Injection API Client.
 * Communicates with authoritative backend endpoints:
 *   - POST /api/environment/fog
 *   - GET /api/environment/fog
 *   - GET /api/environment/events
 */

export interface EnvironmentalStatePayload {
  fog_intensity: number;
  visibility_m: number;
  weather_condition: string;
  fog_factor: number;
  source: string;
  timestamp: number;
  confidence: number;
  is_injected: boolean;
  active_policy: string;
  v_safe_baseline_mps: number;
  v_safe_mps: number;
  constraint_reason: string;
}

export interface VehicleGovernorStatePayload {
  vehicle_id: string;
  vmax_mps: number;
  vmax_kmh: number;
  vmax_provenance: string;
  fog_factor: number;
  v_safe_mps: number;
  requested_speed_mps: number;
  applied_speed_mps: number;
  clamp_active: boolean;
  governor_state: string;
  governor_reason: string;
  motor_driver: string;
}

export interface CausalEventPayload {
  event_id: string;
  timestamp: number;
  category: "WEATHER_EVENT" | "SAFETY_EVENT" | "GOVERNOR_EVENT";
  description: string;
  metadata: Record<string, unknown>;
}

export interface EnvironmentFogResponse {
  environment: EnvironmentalStatePayload;
  vehicles: Record<string, VehicleGovernorStatePayload>;
  recent_events: CausalEventPayload[];
}

import { API_BASE_URL } from "./healthClient";

export async function getEnvironmentFog(): Promise<EnvironmentFogResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/environment/fog`);
    if (!res.ok) return null;
    return (await res.json()) as EnvironmentFogResponse;
  } catch {
    return null;
  }
}

export async function getEnvironmentEvents(limit = 20): Promise<CausalEventPayload[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/environment/events?limit=${limit}`);
    if (!res.ok) return [];
    const data = await res.json();
    return (data.events as CausalEventPayload[]) ?? [];
  } catch {
    return [];
  }
}
