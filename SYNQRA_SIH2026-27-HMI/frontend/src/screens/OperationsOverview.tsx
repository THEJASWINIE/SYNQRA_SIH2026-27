/**
 * S1 Digital Twin - THE LIVE MINE SITE DIGITAL TWIN.
 *
 * This screen answers one question: what is happening in the mine right now?
 *
 *   1. the 2D mine site        2. the fleet operating in it
 *
 * It deliberately shows nothing else. Alerts, fog, bottleneck and KPI panels used to be
 * duplicated here; each has its own screen, and stacking them above the map made the map
 * a secondary citizen on the screen that is supposed to BE the twin. Nothing was deleted -
 * every one of those panels is still reachable on its own screen.
 *
 * System mode and connection live in the shell, above this screen, so they are visible
 * everywhere rather than only here.
 *
 * Every value rendered here is SUPPLIED. This module computes no operational value.
 */

import { EmptyState, Panel } from "../components/primitives";
import { VehicleCard } from "../components/VehicleCard";
import { fleetSummary } from "../state/derive";
import { viewFreshness } from "../state/freshness";
import { bailadilaDeposit5, toDecimalExtent } from "../state/geoSite";
import { useAppState, useFreshnessConfig, useNowMs } from "../state/useAppState";
import { positionsFor, providerForMode, type SystemMode } from "../state/vehiclePosition";
import { GeoSiteMap } from "./GeoSiteMap";

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

  const fleet = fleetSummary(state);
  const vehicles = Object.values(state.vehicles).sort((a, b) =>
    a.vehicleId.localeCompare(b.vehicleId),
  );

  return (
    <section className="hmi-screen" aria-label="Digital Twin">
      <div className="grid-2">
        <GeoSiteMap
          site={geoSite}
          positions={geoPositions}
          mode={state.connection.provider}
          onSelectVehicle={onSelectVehicle}
        />

        {/* THE FLEET OPERATING IN THAT SITE. Live vehicles only. */}
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
      </div>
    </section>
  );
}
