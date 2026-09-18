/**
 * Driver screen — the dumper operator's single-vehicle safety/action display (spec §8–§11).
 *
 * ==========================================================================
 *  EVERY VALUE ON THIS SCREEN IS SUPPLIED. NOTHING HERE IS COMPUTED.
 *
 *  Actual speed, v_safe, command, visibility, gap, H_safe, lead, grade, friction, road
 *  condition, active constraint, risk, link states and the dispatch instruction all come
 *  from the canonical Twin through `projectVehicle`. Absence renders as UNAVAILABLE -
 *  never as 0 and never as a reassuring default. The dominant state is ranked from those
 *  supplied values by `driverState.ts` and never becomes more permissive when data is
 *  missing or stale.
 * ==========================================================================
 *
 * OPERATOR-HMI-01: laid out as a card dashboard (status / map / peer, then safety /
 * communication / provenance, then a compact command bar) instead of a flat cell grid.
 * The data underneath is unchanged - this file only rearranges the same supplied values
 * and the same reason strings `communication.ts` already produces. The map is embedded
 * here (rather than as a sibling panel) so the operator sees it without expanding the
 * technician detail; it is still the one shared `GeoSiteMap`/`VehicleMapPanel`, no second
 * geometry. Commands still go through `buildCommandPayload` / `submitCommand` - the same
 * gateway path as the full `CommandPanel` kept in the technician detail below.
 *
 * Shared by truck01 and truck02: the projection decides which vehicle, not this file.
 */

import { useState } from "react";

import { submitCommand } from "../api/commandClient";
import { TrackGutter, useTrackLayout } from "../components/TrackLayout";
import {
  DATA_STATE_TEXT,
  type DataState,
  provenanceLabel,
  UNAVAILABLE_LABEL,
  vehicleProvenanceLabel,
  viewDataState,
} from "../state/dataStatus";
import {
  buildCommandPayload,
  type DispatchAction,
  nextCommandId,
  outcomeDetail,
  outcomeLabel,
  requiresConfirmation,
} from "../state/dispatchCommand";
import { formatAge, viewFreshness } from "../state/freshness";
import { deriveOperatorReadout, toKmh } from "../state/operatorAction";
import { useHmi } from "../state/ProviderHost";
import { actualSpeedSourceText } from "../state/speedContract";
import { useAppState } from "../state/useAppState";
import {
  backendLink,
  communicationLinks,
  LINK_STATE_GLYPH,
  LINK_STATE_TEXT,
  type LinkStatus,
} from "./communication";
import {
  DRIVER_ACTION_TEXT,
  DRIVER_STATE_TEXT,
  deriveDriverState,
  FOLLOWING_STATUS_TEXT,
  fogBand,
  followingStatus,
  gradePercent,
} from "./driverState";
import { VehicleMapPanel } from "./panels";
import type { VehicleHmiConfig } from "./vehicleConfig";
import type { VehicleProjection } from "./vehicleProjection";

function kmh(mps: number | null | undefined): string {
  const value = toKmh(mps);
  return value === null ? UNAVAILABLE_LABEL : `${value.toFixed(0)} km/h`;
}

/**
 * One line under a link cell: the peer the EVIDENCE names, each radio metric with its own
 * source, the frame sequence and the evidence age. Nothing here is borrowed from another
 * link; an absent metric prints as UNAVAILABLE under its own label.
 */
function linkSub(link: {
  peerId?: string | undefined;
  sequence?: number | null | undefined;
  ageS?: number | null | undefined;
  metrics: readonly {
    label: string;
    value: string;
    unit?: string | undefined;
    available: boolean;
    provenance: string;
  }[];
  bearer: string;
}): string {
  const parts: string[] = [];
  parts.push(link.peerId ? `PEER ${link.peerId}` : "PEER UNAVAILABLE");
  for (const m of link.metrics) {
    parts.push(
      m.available
        ? `${m.label} ${m.value}${m.unit ? ` ${m.unit}` : ""} · ${m.provenance}`
        : `${m.label} ${UNAVAILABLE_LABEL}`,
    );
  }
  if (link.sequence !== null && link.sequence !== undefined) parts.push(`SEQ ${link.sequence}`);
  if (link.ageS !== null && link.ageS !== undefined) parts.push(`${link.ageS.toFixed(1)} s ago`);
  return parts.join(" · ");
}

function metres(value: number | null | undefined): string {
  return value === null || value === undefined || !Number.isFinite(value)
    ? UNAVAILABLE_LABEL
    : `${value.toFixed(0)} m`;
}

/** Short version of a link's own reason, for the operational-notes list. Real text, not new copy. */
function noteFor(link: LinkStatus): string {
  return `${link.label} ${LINK_STATE_TEXT[link.state]}: ${link.reason}`;
}

function Cell({
  label,
  value,
  sub,
  emphasis = false,
}: {
  label: string;
  value: string;
  sub?: string | null;
  emphasis?: boolean;
}) {
  return (
    <div className={`drv-cell${emphasis ? " drv-cell-em" : ""}`}>
      <div className="drv-cell-label">{label}</div>
      <div className="drv-cell-value">{value}</div>
      {sub ? <div className="drv-cell-sub">{sub}</div> : null}
    </div>
  );
}

/** A small labelled row inside a card - two columns, no emphasis. */
function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="op-row">
      <span className="op-row-label">{label}</span>
      <span className="op-row-value">{value}</span>
    </div>
  );
}

function Pill({
  text,
  tone = "neutral",
}: {
  text: string;
  tone?: "ok" | "warn" | "crit" | "neutral";
}) {
  return <span className={`op-pill op-pill-${tone}`}>{text}</span>;
}

/** ok/warn/crit tone for a freshness word. Text still carries the meaning (NFR-008). */
function freshnessTone(state: DataState): "ok" | "warn" | "crit" | "neutral" {
  if (state === "CURRENT") return "ok";
  if (state === "STALE") return "warn";
  return "neutral";
}

function linkTone(state: LinkStatus["state"]): "ok" | "warn" | "crit" | "neutral" {
  if (state === "CONNECTED") return "ok";
  if (state === "STALE") return "warn";
  if (state === "DISCONNECTED") return "crit";
  return "neutral";
}

/**
 * Resizable operator deck: side columns and the first two card rows. The viewer drags the
 * gutters to give any card the room it needs; the page itself never scrolls and the map
 * column keeps at least 40% of the deck. Presentation state only.
 */
const OPERATOR_TRACKS = {
  left: { axis: "x", index: 0, minPx: 200, maxPx: 560 },
  right: { axis: "x", index: 2, minPx: 220, maxPx: 600 },
  row2: { axis: "y", index: 1, minPx: 90, maxPx: 520 },
  row3: { axis: "y", index: 2, minPx: 80, maxPx: 520 },
} as const;

export function DriverScreen({
  projection,
  config,
}: {
  projection: VehicleProjection;
  config: VehicleHmiConfig;
}) {
  const state = useAppState();
  const { freshness } = useHmi();
  const tracks = useTrackLayout(`operator-${config.vehicleId}`, OPERATOR_TRACKS);
  const { vehicle, safety, road, dispatch, connection } = projection;

  const nowMs = Date.parse(state.clock.now);
  const safetyView = viewFreshness(safety?.timestamp ?? null, freshness, nowMs);
  const vehicleView = viewFreshness(vehicle?.timestamp ?? null, freshness, nowMs);

  const readout = deriveOperatorReadout(safety, vehicle);
  const backend = backendLink(vehicle, connection.status);
  const driver = deriveDriverState({
    readout,
    safety,
    vehicle,
    safetyData: viewDataState(safetyView),
    vehicleData: viewDataState(vehicleView),
    backendLink: backend.state,
  });

  const links = communicationLinks(vehicle, connection.status, connection.provider);
  const v2v = links.find((l) => l.label === "V2V") as LinkStatus;
  const v2i = links.find((l) => l.label === "V2I") as LinkStatus;
  const vehicleDataState = viewDataState(vehicleView);

  const visibility = road?.visibility?.value ?? null;
  const fog = fogBand(visibility);
  const following = followingStatus(safety);
  const grade = gradePercent(vehicle?.gradeRad ?? road?.grade ?? null);
  const friction = vehicle?.frictionEst ?? road?.friction ?? null;
  const roadId = vehicle?.position?.segmentId ?? road?.segmentId ?? null;

  const age = formatAge(safetyView.ageMs);
  const vehicleAge = formatAge(vehicleView.ageMs);
  const leadText = !safety
    ? UNAVAILABLE_LABEL
    : (safety.leadVehicleId ??
      (safety.provenance && !safety.provenance.lead_vehicle_id ? UNAVAILABLE_LABEL : "NONE"));
  const safeSpeedSub = [
    readout.action === "SLOW_DOWN" ? "SLOW DOWN" : null,
    safety?.provenance?.v_safe_mps ? provenanceLabel(safety.provenance.v_safe_mps) : null,
    safety && safetyView.quality === "STALE" ? `STALE${age ? ` ${age}` : ""}` : null,
  ]
    .filter((part): part is string => part !== null)
    .join(" · ");
  const peerView = viewFreshness(projection.peer?.timestamp ?? null, freshness, nowMs);
  const peerAge = formatAge(peerView.ageMs);
  const peerStale = peerView.quality === "STALE" ? ` · STALE${peerAge ? ` ${peerAge}` : ""}` : "";
  const speedSub = [
    actualSpeedSourceText(readout.actualSpeed),
    readout.actualSpeed.disagreesWithEvaluated
      ? `SAFETY EVALUATED AT ${kmh(readout.actualSpeed.evaluatedMps)}`
      : null,
    vehicleView.quality === "STALE" ? `STALE${vehicleAge ? ` ${vehicleAge}` : ""}` : null,
  ]
    .filter((part): part is string => part !== null)
    .join(" · ");
  const dispatchText = dispatch
    ? `${dispatch.state}${dispatch.targetSpeed !== null ? ` · target ${kmh(dispatch.targetSpeed)}` : ""}`
    : "NO INSTRUCTION";

  // -- compact command bar: HOLD / STOP / TARGET_SPEED, same gateway path as CommandPanel --
  const [targetSpeedRaw, setTargetSpeedRaw] = useState("");
  const [confirmingStop, setConfirmingStop] = useState(false);
  const [busy, setBusy] = useState<DispatchAction | null>(null);
  const [result, setResult] = useState<{ outcome: string; message: string } | null>(null);

  const send = async (action: DispatchAction) => {
    const built = buildCommandPayload(
      {
        vehicleId: config.vehicleId,
        action,
        targetSpeedRaw,
        reason: `VEHICLE_HMI_${config.vehicleId}`,
      },
      nextCommandId(config.vehicleId, action),
    );
    if (!built.ok) {
      setResult({ outcome: "INVALID", message: built.error });
      return;
    }
    setBusy(action);
    const response = await submitCommand(built.payload);
    setBusy(null);
    setConfirmingStop(false);
    setResult({ outcome: response.outcome, message: response.message });
  };

  const onStop = () => {
    if (requiresConfirmation("STOP") && !confirmingStop) {
      setConfirmingStop(true);
      return;
    }
    void send("STOP");
  };

  return (
    <section
      className={`drv op-dash drv-${driver.state.toLowerCase().replace(/_/g, "-")}`}
      data-driver-state={driver.state}
      aria-label={`${config.displayName} driver display`}
      style={tracks.style}
      data-track-grid="operator"
    >
      <div className="drv-banner" role="status" aria-live="assertive">
        <div className="drv-banner-id mono">{config.displayName}</div>
        <div className="drv-banner-state">{DRIVER_STATE_TEXT[driver.state]}</div>
        <div className="drv-banner-action">{DRIVER_ACTION_TEXT[driver.state]}</div>
        <div className="drv-banner-why">{driver.why}</div>
        <div className="drv-banner-meta faint">
          {readout.reason
            ? `ACTIVE CONSTRAINT: ${readout.reason}`
            : "ACTIVE CONSTRAINT: UNAVAILABLE"}
          {" · "}
          {`RISK: ${safety?.riskLevel ?? UNAVAILABLE_LABEL}`}
          {" · "}
          {age ? `DATA AGE ${age}` : "DATA AGE UNAVAILABLE"}
          {safetyView.quality === null ? " (staleness not evaluated)" : ""}
        </div>
      </div>

      {/* ROW 1 — vehicle status | mine-site map | vehicle/peer */}
      <div className="op-grid op-grid-3">
        <div className="op-card">
          <div className="op-card-head">
            <div className="op-card-headings">
              <div className="op-card-title">{config.displayName}</div>
              <div className="op-card-sub">AUTONOMOUS HAUL TRUCK</div>
            </div>
            <Pill text={DATA_STATE_TEXT[vehicleDataState]} tone={freshnessTone(vehicleDataState)} />
          </div>
          <Cell label="SPEED" value={kmh(readout.actualSpeedMps)} sub={speedSub} emphasis />
          <Cell
            label="COMMAND / TARGET"
            value={kmh(dispatch?.targetSpeed ?? null)}
            sub={dispatch?.reasonCode ? `reason ${dispatch.reasonCode}` : null}
          />
          <Row label="MODE" value={vehicle?.mode ?? UNAVAILABLE_LABEL} />
          <Row
            label="DATA FRESHNESS"
            value={vehicleAge ? `Last telemetry ${vehicleAge}` : "no telemetry timestamp"}
          />
        </div>

        <div className="op-card op-card-map">
          <VehicleMapPanel projection={projection} mode={connection.provider} />
        </div>

        <div className="op-card">
          <div className="op-section-label">OWN VEHICLE</div>
          <div className="op-peer-name mono">{config.displayName}</div>
          <Row label="Speed" value={kmh(readout.actualSpeedMps)} />
          <Row label="Mode" value={vehicle?.mode ?? UNAVAILABLE_LABEL} />
          <Row
            label="Source"
            value={actualSpeedSourceText(readout.actualSpeed) ?? UNAVAILABLE_LABEL}
          />

          <div className="op-section-label op-section-label-spaced">PEER VEHICLE</div>
          <div className="op-peer-name mono">{projection.peerVehicleId ?? UNAVAILABLE_LABEL}</div>
          <Cell
            label={`PEER ${projection.peerVehicleId ?? ""}`.trim()}
            value={projection.peer ? kmh(projection.peer.speedMps) : UNAVAILABLE_LABEL}
            sub={
              projection.peer
                ? `${projection.peer.mode} · ${vehicleProvenanceLabel(projection.peer)}${peerStale} · RISK ${projection.peerSafety?.riskLevel ?? UNAVAILABLE_LABEL}`
                : "not carried by the Twin"
            }
          />
        </div>
      </div>

      {/* ROW 2 — safety | communication | telemetry provenance + operational notes */}
      <div className="op-grid op-grid-3">
        <div className="op-card">
          <div className="op-card-head">
            <span className="op-card-icon" aria-hidden="true">
              🛡
            </span>
            <div className="op-card-headings">
              <div className="op-card-title">SAFETY</div>
            </div>
            <Pill
              text={
                driver.state === "SAFE" || driver.state === "FOLLOWING" ? "NORMAL" : "ATTENTION"
              }
              tone={
                driver.state === "SAFE" || driver.state === "FOLLOWING"
                  ? "ok"
                  : driver.state === "STOP"
                    ? "crit"
                    : "warn"
              }
            />
          </div>
          <div className="op-grid op-grid-2">
            <Cell
              label="SAFE SPEED"
              value={kmh(readout.safeSpeedMps)}
              sub={safeSpeedSub}
              emphasis
            />
            <Cell
              label="RISK LEVEL"
              value={safety?.riskLevel ?? UNAVAILABLE_LABEL}
              sub={
                readout.reason
                  ? `ACTIVE CONSTRAINT ${readout.reason}`
                  : "ACTIVE CONSTRAINT UNAVAILABLE"
              }
            />
          </div>
          <div className="op-grid op-grid-2">
            <Cell label="GAP" value={metres(safety?.headwayCurrent ?? null)} />
            <Cell
              label="REQUIRED GAP (H_safe)"
              value={metres(safety?.hSafe ?? null)}
              sub={`FOLLOWING: ${FOLLOWING_STATUS_TEXT[following]}`}
            />
          </div>
          <Row label="LEAD VEHICLE" value={leadText} />
          <Row
            label="Headway violation"
            value={
              safety?.headwayViolation === null || safety?.headwayViolation === undefined
                ? UNAVAILABLE_LABEL
                : safety.headwayViolation
                  ? "YES"
                  : "NO"
            }
          />
          <Row
            label="Envelope violation"
            value={
              safety?.envelopeViolation === null || safety?.envelopeViolation === undefined
                ? UNAVAILABLE_LABEL
                : safety.envelopeViolation
                  ? "YES"
                  : "NO"
            }
          />
          <Cell
            label="STOPPING MARGIN"
            value={UNAVAILABLE_LABEL}
            sub={
              safety?.envelopeViolation === true
                ? "ENVELOPE VIOLATION"
                : safety?.envelopeViolation === false
                  ? "envelope OK"
                  : "not supplied by the Twin"
            }
          />
        </div>

        <div className="op-card">
          <div className="op-card-head">
            <span className="op-card-icon" aria-hidden="true">
              📡
            </span>
            <div className="op-card-headings">
              <div className="op-card-title">COMMUNICATION</div>
            </div>
          </div>
          <Row label="Backend (WebSocket)" value={LINK_STATE_TEXT[backend.state]} />
          <Row label="Telemetry" value={DATA_STATE_TEXT[vehicleDataState]} />
          <div className="op-link-row">
            <span className="op-row-label">V2V (LoRa)</span>
            <Pill text={LINK_STATE_TEXT[v2v.state]} tone={linkTone(v2v.state)} />
          </div>
          <div className="op-link-sub faint">{linkSub(v2v)}</div>
          <div className="op-link-row">
            <span className="op-row-label">V2I (Infrastructure)</span>
            <Pill text={LINK_STATE_TEXT[v2i.state]} tone={linkTone(v2i.state)} />
          </div>
          <div className="op-link-sub faint">{v2i.bearer}</div>
          <Row
            label="Wi-Fi (Local)"
            value={
              backend.metrics[0]?.available
                ? `${LINK_STATE_TEXT[backend.state]} · RSSI ${backend.metrics[0]?.value}${backend.metrics[0]?.unit ? ` ${backend.metrics[0]?.unit}` : ""}`
                : UNAVAILABLE_LABEL
            }
          />
          {/* Kept as plain cells too: driverScreen.test.tsx / communication.test.tsx parse this exact shape. */}
          <Cell
            label="V2V"
            value={`${LINK_STATE_GLYPH[v2v.state]} ${LINK_STATE_TEXT[v2v.state]}`}
            sub={linkSub(v2v)}
          />
          <Cell
            label="V2I"
            value={`${LINK_STATE_GLYPH[v2i.state]} ${LINK_STATE_TEXT[v2i.state]}`}
            sub={v2i.bearer}
          />
        </div>

        <div className="op-card">
          <div className="op-card-head">
            <span className="op-card-icon" aria-hidden="true">
              📋
            </span>
            <div className="op-card-headings">
              <div className="op-card-title">TELEMETRY PROVENANCE</div>
            </div>
          </div>
          <Row
            label="Position"
            value={vehicle?.positionOdom?.status === "VALID" ? "LOCAL ODOMETRY" : UNAVAILABLE_LABEL}
          />
          <Row label="Position on map" value="NOT DRAWABLE" />
          <Row
            label="Speed"
            value={actualSpeedSourceText(readout.actualSpeed) ?? UNAVAILABLE_LABEL}
          />
          <Row label="Origin" value={vehicleProvenanceLabel(vehicle)} />
          <Row label="Last update" value={vehicleAge ?? UNAVAILABLE_LABEL} />

          <div className="op-section-label op-section-label-spaced">OPERATIONAL NOTES</div>
          <ul className="op-notes">
            <li>
              ℹ {config.displayName} uses local wheel/IMU odometry. This position is not
              geographically surveyed and is not drawn on the mine map.
            </li>
            <li>ℹ {noteFor(v2v)}</li>
            <li>ℹ {noteFor(v2i)}</li>
          </ul>

          {/* Kept as plain cells too: driverScreen.test.tsx / safetyContract.test.tsx parse these verbatim. */}
          <Cell label="LEAD TRUCK" value={leadText} />
          <Cell
            label="ROAD"
            value={roadId ?? UNAVAILABLE_LABEL}
            sub={[
              road?.surfaceState ?? "CONDITION UNAVAILABLE",
              grade === null ? "GRADE UNAVAILABLE" : `${grade >= 0 ? "+" : ""}${grade.toFixed(0)}%`,
            ].join(" | ")}
          />
          <Cell
            label="FRICTION"
            value={
              friction?.value !== null && friction?.value !== undefined
                ? friction.value.toFixed(2)
                : UNAVAILABLE_LABEL
            }
            sub={
              friction?.sigma !== null && friction?.sigma !== undefined
                ? `±${friction.sigma.toFixed(2)}`
                : null
            }
          />
          <Cell label="VISIBILITY" value={metres(visibility)} sub={fog ? `${fog} FOG` : null} />
          <Cell
            label="DISPATCH"
            value={dispatchText}
            sub={dispatch?.routeId ? `route ${dispatch.routeId}` : null}
          />
        </div>
      </div>

      {/* ROW 3 — command / operator actions */}
      <div className="op-card op-command-bar">
        <div className="op-card-head">
          <span className="op-card-icon" aria-hidden="true">
            ⚙
          </span>
          <div className="op-card-headings">
            <div className="op-card-title">COMMAND / OPERATOR ACTIONS</div>
          </div>
        </div>
        <div className="op-command-controls">
          <button
            type="button"
            className="op-btn op-btn-hold"
            onClick={() => void send("HOLD")}
            disabled={busy !== null}
          >
            ⏸ HOLD
          </button>
          <button
            type="button"
            className="op-btn op-btn-stop"
            onClick={onStop}
            disabled={busy !== null}
          >
            ⏹ {confirmingStop ? "CONFIRM STOP" : "STOP"}
          </button>
          <div className="op-target-speed">
            <span className="op-row-label">TARGET SPEED (m/s)</span>
            {readout.safeSpeedMps === null ? (
              <span className="op-target-unavailable">{UNAVAILABLE_LABEL}</span>
            ) : (
              <div className="op-target-input">
                <input
                  value={targetSpeedRaw}
                  aria-label="Target speed"
                  onChange={(event) => setTargetSpeedRaw(event.target.value)}
                />
                <button
                  type="button"
                  onClick={() => void send("TARGET_SPEED")}
                  disabled={busy !== null}
                >
                  SEND
                </button>
              </div>
            )}
          </div>
          <div className="op-command-status">
            <span className="op-row-label">Command status</span>
            <span className="op-row-value">
              {result ? outcomeLabel(result.outcome) : "No command sent"}
            </span>
          </div>
        </div>
        {result ? (
          <div className="op-command-result faint" data-outcome={result.outcome}>
            {outcomeDetail(result.outcome)} {result.message}
          </div>
        ) : null}
        <p className="op-note faint">
          Commands are validated by the safety gateway. TARGET SPEED is unavailable while v_safe is
          not supplied (fail closed) — HOLD and STOP remain available.
        </p>
      </div>

      {/* Resize gutters: explicitly placed grid items; hidden where the deck stacks. */}
      <TrackGutter
        layout={tracks}
        track="left"
        edge="end"
        label="Left column width"
        className="op-gutter-left"
      />
      <TrackGutter
        layout={tracks}
        track="right"
        edge="start"
        label="Right column width"
        className="op-gutter-right"
      />
      <TrackGutter
        layout={tracks}
        track="row2"
        edge="end"
        label="Top row height"
        className="op-gutter-row2"
      />
      <TrackGutter
        layout={tracks}
        track="row3"
        edge="end"
        label="Middle row height"
        className="op-gutter-row3"
      />
    </section>
  );
}
