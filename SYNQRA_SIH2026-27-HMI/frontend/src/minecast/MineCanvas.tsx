/**
 * MineCanvas — the one and only WebGL boundary.
 *
 * ==========================================================================
 *  EVERY THREE.JS IMPORT IN MINE-CAST IS REACHED THROUGH THIS FILE.
 *
 *  `MineCastApp` loads it with `React.lazy`, so:
 *
 *    * server rendering never touches Three.js, which is what keeps the shell testable
 *      in the project's Node test environment (no jsdom, no WebGL - M4D-C);
 *    * the three/fiber/drei bundle is code-split out of the initial page and fetched only
 *      when a spatial view is actually shown;
 *    * a browser without WebGL renders an honest message instead of a blank rectangle.
 *
 *  The projection, the store and all six overlay panels stay entirely free of Three.js.
 *  That boundary is asserted in `minecastArchitecture.test.ts`.
 * ==========================================================================
 *
 * BUILT ONCE, NOT PER FRAME
 *
 * The height grid, the mine features and the camera framing are all memoised on the site
 * dimensions. Telemetry updates re-render the overlay panels; they do not rebuild the
 * landform.
 */

import { Canvas } from "@react-three/fiber";
import { useMemo } from "react";

import { extentSizeMetres, toDecimalExtent } from "../state/geoSite";
import { demoRoutes } from "./demoRoutes";
import { haulCorridors } from "./haulRoads";
import { MineScene } from "./MineScene";
import { overviewFraming } from "./mineCamera";
import type { LayerId, MineCastSite, MineCastVehicle } from "./minecastProjection";
import type { CameraRequest } from "./minecastStore";
import { benchSurfaces, mineFeatures } from "./mineFeatures";
import { mineZones } from "./mineZones";
import type { SpatialPosition } from "./spatialPosition";
import { sampleHeightGrid, terrainConfig } from "./terrainField";

export default function MineCanvas({
  site,
  layerVisibility,
  aspect,
  vehiclePositions,
  vehicles,
  cameraRequest,
  selectedVehicleId,
  onSelectVehicle,
  routeEmphasis = false,
  highlightRouteId = null,
}: {
  site: MineCastSite;
  layerVisibility: Readonly<Record<LayerId, boolean>>;
  /** Viewport aspect, used only for the initial orthographic framing. */
  aspect: number;
  /**
   * MINECAST-01: canonical Twin spatial positions, resolved upstream and passed straight
   * through. A new array re-renders the scene tree, which is what makes R3F redraw a
   * frame under `frameloop="demand"` when a truck moves.
   */
  vehiclePositions: readonly SpatialPosition[];
  vehicles: readonly MineCastVehicle[];
  cameraRequest: CameraRequest | null;
  selectedVehicleId: string | null;
  onSelectVehicle?: ((canonicalVehicleId: string) => void) | undefined;
  /**
   * MINE-ROUTES-02: console route emphasis, and the route id the Twin stamped on the
   * selected truck's pose. The corridors of that route are drawn lighter; the lookup is
   * against the same `demoRoutes` the backend follows, so nothing is guessed.
   */
  routeEmphasis?: boolean;
  highlightRouteId?: string | null;
}) {
  /*
    Site dimensions come from the PUBLISHED coordinate extent's own measured size, so the
    scene is the size the extent describes. The landform inside it is invented; its
    footprint is not arbitrary.
  */
  const { grid, features, surfaces, corridors, zones, routes, framing } = useMemo(() => {
    const size = extentSizeMetres(toDecimalExtent(site.extent));
    const config = terrainConfig(size.widthM, size.heightM);
    return {
      grid: sampleHeightGrid(config),
      features: mineFeatures(config),
      // Shelf / face / floor surfaces, from the same morphology as the crests.
      surfaces: benchSurfaces(config),
      // Same config as the terrain, so corridors drape on the surface they cross.
      corridors: haulCorridors(config),
      // Working area, stockpile, dump: same generator the 2D plan draws.
      zones: mineZones(config),
      routes: demoRoutes(config),
      framing: overviewFraming(size.widthM, size.heightM, aspect),
    };
  }, [site.extent, aspect]);

  const highlightCorridorIds = useMemo(
    () => routes.find((r) => r.routeId === highlightRouteId)?.corridorIds ?? [],
    [routes, highlightRouteId],
  );

  return (
    <Canvas
      // Orthographic: equal distances on screen are equal distances on the ground.
      orthographic
      camera={{
        position: [framing.position[0], framing.position[1], framing.position[2]],
        left: framing.frustum.left,
        right: framing.frustum.right,
        top: framing.frustum.top,
        bottom: framing.frustum.bottom,
        near: framing.frustum.near,
        far: framing.frustum.far,
        zoom: 1,
      }}
      // No continuous render loop: the scene is static, so it redraws only on interaction.
      frameloop="demand"
      dpr={[1, 2]}
      gl={{ antialias: true }}
      style={{ width: "100%", height: "100%", display: "block" }}
    >
      <color attach="background" args={["#0f1216"]} />
      <MineScene
        grid={grid}
        features={features}
        surfaces={surfaces}
        corridors={corridors}
        zones={zones}
        framing={framing}
        layerVisibility={layerVisibility}
        vehiclePositions={vehiclePositions}
        vehicles={vehicles}
        cameraRequest={cameraRequest}
        selectedVehicleId={selectedVehicleId}
        onSelectVehicle={onSelectVehicle}
        routeEmphasis={routeEmphasis}
        highlightCorridorIds={highlightCorridorIds}
      />
    </Canvas>
  );
}
