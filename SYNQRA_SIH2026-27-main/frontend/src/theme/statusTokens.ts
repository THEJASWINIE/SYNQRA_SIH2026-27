/**
 * Status tokens — M1 foundation.
 *
 * NFR-008 requires that critical information never depend on colour alone. This module
 * is the single place a display state is turned into something renderable, and every
 * token carries a `label` and a `glyph` alongside its `colour`. A component that reaches
 * for a colour without the matching text or glyph is a defect.
 *
 * M1 covered connection states only. M4 adds provider-status, system-mode, severity, risk
 * and criticality tokens below, in the same shape and under the same rule.
 */

import type { ConnectionStatus } from "../contracts/appState";
import type {
  AlertSeverity,
  Criticality,
  DispatchState,
  RiskLevel,
  SlotStatus,
  SystemMode,
} from "../contracts/enums";

export type ConnectionState = "idle" | "connecting" | "connected" | "error";

export interface StatusToken {
  /** Human-readable text. Always rendered — this is what survives greyscale. */
  readonly label: string;
  /** Non-colour visual channel. */
  readonly glyph: string;
  /** Colour is an enhancement, never the sole carrier of meaning. */
  readonly colour: string;
}

export const CONNECTION_TOKENS: Readonly<Record<ConnectionState, StatusToken>> = {
  idle: { label: "Idle", glyph: "○", colour: "#6b7280" },
  connecting: { label: "Connecting", glyph: "◐", colour: "#b45309" },
  connected: { label: "Connected", glyph: "●", colour: "#15803d" },
  error: { label: "Unreachable", glyph: "▲", colour: "#b91c1c" },
} as const;

export function connectionToken(state: ConnectionState): StatusToken {
  return CONNECTION_TOKENS[state];
}

// ---------------------------------------------------------------------------
// M4 tokens
//
// Every token below carries a `label` and a `glyph` alongside its `colour`, for the same
// reason the M1 connection tokens do: NFR-008 requires that critical information never
// depend on colour alone. Strip the colour and each state must still read correctly.
// ---------------------------------------------------------------------------

/** Provider lifecycle, as `AppState.connection.status` reports it. */
export const PROVIDER_STATUS_TOKENS: Readonly<Record<ConnectionStatus, StatusToken>> = {
  IDLE: { label: "Idle", glyph: "○", colour: "#6b7280" },
  CONNECTING: { label: "Connecting", glyph: "◐", colour: "#b45309" },
  CONNECTED: { label: "Connected", glyph: "●", colour: "#15803d" },
  RECONNECTING: { label: "Reconnecting", glyph: "◐", colour: "#b45309" },
  DISCONNECTED: { label: "Disconnected", glyph: "▲", colour: "#b91c1c" },
  ERROR: { label: "Provider error", glyph: "▲", colour: "#b91c1c" },
} as const;

export function providerStatusToken(status: ConnectionStatus): StatusToken {
  return PROVIDER_STATUS_TOKENS[status];
}

/**
 * System mode — SUPPLIED on `SystemHealth.systemMode`.
 *
 * There is deliberately no token for "no mode supplied". An unavailable mode is rendered
 * as unavailable by the caller and must never fall back to NORMAL: displaying a
 * reassuring mode nobody supplied is the most dangerous substitution this HMI can make.
 */
export const SYSTEM_MODE_TOKENS: Readonly<Record<SystemMode, StatusToken>> = {
  NORMAL: { label: "NORMAL", glyph: "●", colour: "#15803d" },
  CAUTION: { label: "CAUTION", glyph: "◆", colour: "#b45309" },
  DEGRADED: { label: "DEGRADED", glyph: "◐", colour: "#c2410c" },
  LOCAL_SAFE: { label: "LOCAL-SAFE", glyph: "■", colour: "#b91c1c" },
  STOP_UNSAFE: { label: "STOP / UNSAFE", glyph: "▲", colour: "#7f1d1d" },
} as const;

export function systemModeToken(mode: SystemMode): StatusToken {
  return SYSTEM_MODE_TOKENS[mode];
}

/** Alert severity — SUPPLIED. Never assigned or promoted by the HMI. */
export const SEVERITY_TOKENS: Readonly<Record<AlertSeverity, StatusToken>> = {
  INFO: { label: "INFO", glyph: "ℹ", colour: "#1d4ed8" },
  WARNING: { label: "WARNING", glyph: "◆", colour: "#b45309" },
  CRITICAL: { label: "CRITICAL", glyph: "▲", colour: "#b91c1c" },
} as const;

export function severityToken(severity: AlertSeverity): StatusToken {
  return SEVERITY_TOKENS[severity];
}

/**
 * Risk level — SUPPLIED on `SafetyState.riskLevel`.
 *
 * `UNKNOWN` has its own token and renders as unknown. It is never shown as LOW, never
 * blank, and never omitted — band names are undefined in the specification (AMB-007) and
 * the HMI does not re-band a supplied level.
 */
export const RISK_TOKENS: Readonly<Record<RiskLevel, StatusToken>> = {
  LOW: { label: "LOW", glyph: "●", colour: "#15803d" },
  MODERATE: { label: "MODERATE", glyph: "◆", colour: "#b45309" },
  HIGH: { label: "HIGH", glyph: "◆", colour: "#c2410c" },
  CRITICAL: { label: "CRITICAL", glyph: "▲", colour: "#b91c1c" },
  UNKNOWN: { label: "UNKNOWN", glyph: "?", colour: "#6b7280" },
} as const;

export function riskToken(level: RiskLevel): StatusToken {
  return RISK_TOKENS[level];
}

/** Bottleneck criticality — SUPPLIED. */
export const CRITICALITY_TOKENS: Readonly<Record<Criticality, StatusToken>> = {
  LOW: { label: "LOW", glyph: "●", colour: "#15803d" },
  MEDIUM: { label: "MEDIUM", glyph: "◆", colour: "#b45309" },
  HIGH: { label: "HIGH", glyph: "◆", colour: "#c2410c" },
  CRITICAL: { label: "CRITICAL", glyph: "▲", colour: "#b91c1c" },
  UNKNOWN: { label: "UNKNOWN", glyph: "?", colour: "#6b7280" },
} as const;

export function criticalityToken(level: Criticality): StatusToken {
  return CRITICALITY_TOKENS[level];
}

// ---------------------------------------------------------------------------
// M7 tokens — S4 Dispatch & Slots
// ---------------------------------------------------------------------------

/**
 * Slot status — SUPPLIED on `SlotState.status`.
 *
 * `CONFLICT` carries a distinct glyph as well as a distinct colour, because FR-009 AC3
 * requires conflicting slots to be flagged visually *and* textually. `UNKNOWN` has its
 * own token and is never shown as `RESERVED`.
 */
export const SLOT_STATUS_TOKENS: Readonly<Record<SlotStatus, StatusToken>> = {
  RESERVED: { label: "RESERVED", glyph: "▢", colour: "#6aa9ff" },
  ACTIVE: { label: "ACTIVE", glyph: "●", colour: "#15803d" },
  RELEASED: { label: "RELEASED", glyph: "○", colour: "#6b7280" },
  EXPIRED: { label: "EXPIRED", glyph: "×", colour: "#6b7280" },
  CONFLICT: { label: "CONFLICT", glyph: "▲", colour: "#b91c1c" },
  UNKNOWN: { label: "UNKNOWN", glyph: "?", colour: "#6b7280" },
} as const;

export function slotStatusToken(status: SlotStatus): StatusToken {
  return SLOT_STATUS_TOKENS[status];
}

/**
 * Dispatch command state — SUPPLIED on `DispatchCommand.state`.
 *
 * FR-010 AC2 requires recommended and issued to be distinguishable. These describe WHAT
 * THE PRODUCER REPORTS. `ISSUED` is not permission for the HMI to issue anything —
 * AMB-008 is unresolved and M7D-A declines to rule on it.
 */
export const DISPATCH_STATE_TOKENS: Readonly<Record<DispatchState, StatusToken>> = {
  RECOMMENDED: { label: "RECOMMENDED", glyph: "◇", colour: "#b45309" },
  ISSUED: { label: "ISSUED", glyph: "◆", colour: "#1d4ed8" },
  ACKNOWLEDGED: { label: "ACKNOWLEDGED", glyph: "✓", colour: "#15803d" },
  SUPERSEDED: { label: "SUPERSEDED", glyph: "↷", colour: "#6b7280" },
  REJECTED: { label: "REJECTED", glyph: "×", colour: "#b91c1c" },
} as const;

export function dispatchStateToken(state: DispatchState): StatusToken {
  return DISPATCH_STATE_TOKENS[state];
}
