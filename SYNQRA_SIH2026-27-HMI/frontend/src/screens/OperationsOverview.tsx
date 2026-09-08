/**
 * S1 Operations Overview — M4.
 *
 * Answers, in this order and without scrolling past a chart to reach a warning:
 *
 *   1. critical alerts       2. where the vehicles are      3. where the bottleneck is
 *   4. fog / visibility      5. is the fleet operating       6. is the data fresh
 *
 * System mode and connection live in the shell, above this screen, so they are visible on
 * every screen rather than only this one.
 *
 * Every value rendered here is SUPPLIED. This module computes no operational value: it
 * orders, selects among, formats and compares values the data layer already delivered.
 */

import { AlertRow } from "../components/AlertRow";
import { EmptyState, MetricCard, Panel, StatusBadge } from "../components/primitives";
import { VehicleCard } from "../components/VehicleCard";
import { mergedAlerts, STALE_ALERTING_INACTIVE_TEXT } from "../state/alerts";
import { activeBottleneck, fleetSummary, fmt, worstVisibility } from "../state/derive";
import { viewFreshness } from "../state/freshness";
import { bailadilaDeposit5, toDecimalExtent } from "../state/geoSite";
import { positionsFor, providerForMode, type SystemMode } from "../state/vehiclePosition";
import { useAppState, useFreshnessConfig, useNowMs } from "../state/useAppState";
import { criticalityToken } from "../theme/statusTokens";
import { MineMap } from "./MineMap";
import { GeoSiteMap } from "./GeoSiteMap";
import { ScenarioPicker } from "./ScenarioPicker";

export function OperationsOverview({
  onSelectVehicle,
}: {
  /** Opens S2 Vehicle Detail. Selection is UI state and lives in the shell. */
  onSelectVehicle: (vehicleId: string) => void;
}) {
  const state = useAppState();
  const config = useFreshnessConfig();
  const nowMs = useNowMs();

  const fresh = (timestamp: string | null | undefined) => viewFreshness(timestamp, config, nowMs);

  /**
   * Geospatial prototype state. The site model is static published data; the positions
   * come from the provider that matches the ACTIVE MODE, with no fallback between modes.
   */
  const geoSite = bailadilaDeposit5();
  const geoPositions = positionsFor(
    state.vehicles,
    providerForMode(state.connection.provider as SystemMode, toDecimalExtent(geoSite.extent)),
  );

  /**
   * Supplied alerts plus the HMI's own data-path alerts (M8D-A). Derived alerts are view
   * data only — they are never written back into the store, and they never overwrite a
   * supplied alert.
   */
  const merged = mergedAlerts(state, config, nowMs);
  const ranked = merged.all.filter((a) => a.active);
  const critical = ranked.filter((a) => a.severity === "CRITICAL");
  const bottleneck = activeBottleneck(state.bottlenecks);
  const visibility = worstVisibility(state.road);
  const fleet = fleetSummary(state);
  const vehicles = Object.values(state.vehicles).sort((a, b) =>
    a.vehicleId.localeCompare(b.vehicleId),
  );

  return (
    <>
      {/* 1 — ALERTS. Above the map and above every metric, deliberately. */}
      <Panel
        title="Active alerts"
        note={
          ranked.length > 0
            ? `${critical.length} critical of ${ranked.length} active · ${merged.derived.length} from the HMI data path`
            : "supplied by the data layer"
        }
      >
        {ranked.length === 0 ? (
          <EmptyState
            headline="NO ACTIVE ALERTS"
            detail="The data layer has supplied no active alert, and no HMI data-path condition is present. Nothing is inferred or manufactured to fill this panel."
          />
        ) : (
          ranked.map((alert) => (
            <AlertRow key={alert.alertId} alert={alert} freshness={fresh(alert.timestamp)} />
          ))
        )}
        {merged.staleAlertingActive ? null : (
          <p className="unresolved">{STALE_ALERTING_INACTIVE_TEXT} (AMB-014).</p>
        )}
      </Panel>

      {/* 2 — MAP AND FLEET */}
      <div className="grid-2">
        <Panel
          title="Mine map"
          note={
            state.topology
              ? `${state.topology.nodes.length} nodes · ${state.topology.segments.length} segments`
              : undefined
          }
        >
          <MineMap state={state} />
        </Panel>

      {/*
        GEOSPATIAL DIGITAL TWIN PROTOTYPE — Bailadila Deposit-5.

        Rendered beside the abstract topology map, never merged with it: one is a graph in
        topology units, the other is geographic. The position provider is chosen from the
        ACTIVE PROVIDER, so LIVE gets the physical provider (always UNAVAILABLE) and can
        never inherit simulated coordinates.
      */}
      <GeoSiteMap
        site={geoSite}
        positions={geoPositions}
        mode={state.connection.provider}
        onSelectVehicle={onSelectVehicle}
      />

        <Panel title="Scenario (developer / tester)" note="FR-019">
          <ScenarioPicker />
        </Panel>
      </div>

      {/* 3 — FOG / VISIBILITY and BOTTLENECK */}
      <div className="grid-2">
        <Panel title="Fog / visibility" note="supplied">
          {visibility === null ? (
            <EmptyState
              headline="VISIBILITY DATA UNAVAILABLE"
              detail="No segment carries a supplied visibility reading."
            />
          ) : (
            <div className="metrics">
              <MetricCard
                label="Worst visibility"
                value={fmt(visibility.visibilityM, 0)}
                unit="m"
                footer={`segment ${visibility.segmentId}`}
              />
              <MetricCard
                label="Uncertainty (σ)"
                value={fmt(visibility.sigma, 1)}
                unit="m"
                footer="supplied"
              />
            </div>
          )}
          {state.topology && Object.keys(state.forecasts).length > 0 ? (
            <p className="faint" style={{ marginTop: "0.5rem" }}>
              {Object.keys(state.forecasts).length} supplied visibility forecast(s) available.
              Forecast presentation is S3/S5 scope, not S1.
            </p>
          ) : null}
        </Panel>

        <Panel title="Active bottleneck" note="ranked by supplied score">
          {bottleneck === null ? (
            <EmptyState
              headline="NO ACTIVE BOTTLENECK"
              detail="The data layer has supplied no bottleneck state. Task 1 does not compute one."
            />
          ) : (
            <>
              <div style={{ marginBottom: "0.5rem" }}>
                <span className="mono">{bottleneck.nodeId}</span>{" "}
                <StatusBadge token={criticalityToken(bottleneck.criticality)} />
              </div>
              <div className="metrics">
                <MetricCard label="Score" value={fmt(bottleneck.bottleneckScore, 2)} />
                <MetricCard label="Queue" value={fmt(bottleneck.queue, 0)} unit="veh" />
                <MetricCard label="Utilization" value={fmt(bottleneck.utilization, 2)} />
                <MetricCard label="Arrival λ" value={fmt(bottleneck.lambdaVph, 0)} unit="vph" />
                <MetricCard label="Service μ" value={fmt(bottleneck.muVph, 0)} unit="vph" />
              </div>
            </>
          )}
        </Panel>
      </div>

      {/* 4 — FLEET */}
      <Panel
        title="Fleet"
        note={`${fleet.total} vehicles · ${fleet.withPosition} positioned · ${fleet.overSafeSpeed} over safe speed`}
      >
        {vehicles.length === 0 ? (
          <EmptyState
            headline="NO VEHICLES SUPPLIED"
            detail="No vehicle state has been received for this scenario yet."
          />
        ) : (
          <div className="grid-auto">
            {vehicles.map((vehicle) => (
              <VehicleCard
                key={vehicle.vehicleId}
                vehicle={vehicle}
                safety={state.safety[vehicle.vehicleId]}
                freshness={fresh(vehicle.timestamp)}
                onSelect={onSelectVehicle}
              />
            ))}
          </div>
        )}
      </Panel>

      {/* 5 — KPIs, last. */}
      <Panel title="Throughput / KPIs" note="supplied by the data layer">
        {state.kpis === null ? (
          <EmptyState
            headline="KPI DATA UNAVAILABLE"
            detail="No KPI snapshot has been supplied. Task 1 does not generate KPIs."
          />
        ) : (
          <div className="metrics">
            <MetricCard label="Throughput" value={fmt(state.kpis.throughputTph, 1)} unit="t/h" />
            <MetricCard label="Cycle time" value={fmt(state.kpis.cycleTimeS, 0)} unit="s" />
            <MetricCard label="Avg queue" value={fmt(state.kpis.queueLengthAvg, 1)} unit="veh" />
            <MetricCard label="Utilization" value={fmt(state.kpis.utilization, 2)} />
            <MetricCard label="Stops" value={fmt(state.kpis.stopsCount, 0)} />
            <MetricCard
              label="Envelope violations"
              value={fmt(state.kpis.safetyEnvelopeViolations, 0)}
            />
          </div>
        )}
      </Panel>
    </>
  );
}
