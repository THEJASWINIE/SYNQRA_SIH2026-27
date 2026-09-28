/**
 * Scene assembly — lights, camera, terrain, mine geometry, published extent.
 *
 * ==========================================================================
 *  THE EXTENT RECTANGLE IS THE ONLY REAL GEOMETRY IN THIS SCENE.
 *
 *  Four published coordinate extrema define a box, and drawing a box from them invents
 *  nothing. Everything else here - the landform, the pit, the benches - is
 *  SYNTHETIC_FOR_DEMO.
 *
 *  So the extent is drawn in the one accent colour the scene allows itself, DASHED, and
 *  captioned PUBLISHED COORDINATE EXTENT / NOT A LEASE BOUNDARY in the overlay. Dashed
 *  rather than solid because a solid outline reads as a surveyed boundary, which this is
 *  explicitly not.
 * ==========================================================================
 *
 * WHAT IS DRAWN, AND ON WHOSE AUTHORITY
 *
 * MINECAST-01 added the vehicles, driven by the Twin exactly as this file always said
 * they would be: their coordinates are the canonical `position_scene` the 2D consoles
 * already draw, and a marker appears only where the Twin actually placed one.
 *
 * STILL DELIBERATELY ABSENT
 *
 * No routes, no corridor STATE, no safety corridors, no V2V links. Those need link or
 * route evidence the Twin does not supply, and drawing a placeholder for any of them
 * would be the exact fabrication this project exists to avoid.
 *
 * WebGL only. Not unit tested (M4D-C); the camera and geometry maths it consumes are
 * asserted in `scene.test.ts`.
 */

import { MapControls } from "@react-three/drei";
import { useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import { BufferAttribute, BufferGeometry, Line, LineDashedMaterial } from "three";
import type { MapControls as MapControlsImpl } from "three-stdlib";
import { HaulRoadsLayer } from "./HaulRoadsLayer";
import type { HaulCorridor } from "./haulRoads";
import { MineGeometryOverlay } from "./MineGeometry";
import { MineTerrain } from "./MineTerrain";
import type { CameraFraming } from "./mineCamera";
import type { LayerId, MineCastVehicle } from "./minecastProjection";
import type { CameraRequest } from "./minecastStore";
import type { BenchSurface, MineFeature } from "./mineFeatures";
import type { MineZone } from "./mineZones";
import { MineZonesLayer } from "./MineZonesLayer";
import type { SpatialPosition } from "./spatialPosition";
import type { HeightGrid } from "./terrainField";
import { VehicleMarkers } from "./VehicleMarkers";

/**
 * The published coordinate extent, as a dashed rectangle draped just above the terrain's
 * highest point so it is never buried by the landform.
 */
function PublishedExtentOutline({
  widthM,
  heightM,
  elevationM,
}: {
  widthM: number;
  heightM: number;
  elevationM: number;
}) {
  const line = useMemo(() => {
    // Five points: four corners, closing back on the first.
    const corners: readonly (readonly [number, number])[] = [
      [0, 0],
      [widthM, 0],
      [widthM, heightM],
      [0, heightM],
      [0, 0],
    ];

    const positions = new Float32Array(corners.length * 3);
    corners.forEach(([x, z], index) => {
      positions[index * 3] = x;
      positions[index * 3 + 1] = elevationM;
      positions[index * 3 + 2] = z;
    });

    const geometry = new BufferGeometry();
    geometry.setAttribute("position", new BufferAttribute(positions, 3));

    const built = new Line(
      geometry,
      new LineDashedMaterial({
        color: 0xf2a54a,
        dashSize: 45,
        gapSize: 30,
        transparent: true,
        opacity: 0.95,
      }),
    );
    // Without this the dashes do not appear at all.
    built.computeLineDistances();
    return built;
  }, [widthM, heightM, elevationM]);

  return <primitive object={line} />;
}

export function MineScene({
  grid,
  features,
  surfaces,
  corridors,
  zones,
  framing,
  layerVisibility,
  vehiclePositions,
  vehicles,
  cameraRequest,
  selectedVehicleId,
  onSelectVehicle,
  routeEmphasis = false,
  highlightCorridorIds = [],
}: {
  grid: HeightGrid;
  features: readonly MineFeature[];
  surfaces: readonly BenchSurface[];
  corridors: readonly HaulCorridor[];
  /** MINE-ROUTES-02: synthetic operational zones, from the same generator as the plan. */
  zones: readonly MineZone[];
  framing: CameraFraming;
  layerVisibility: Readonly<Record<LayerId, boolean>>;
  /**
   * MINECAST-01: spatial positions resolved from the canonical Twin upstream. The scene
   * draws them; it does not compute, adjust or default any of them.
   */
  vehiclePositions: readonly SpatialPosition[];
  /** The projected fleet, for the callout figures. Joined to positions by id downstream. */
  vehicles: readonly MineCastVehicle[];
  /** MINECAST-03: one-shot camera request from the DOM map controls, applied on `seq`. */
  cameraRequest: CameraRequest | null;
  selectedVehicleId: string | null;
  onSelectVehicle?: ((canonicalVehicleId: string) => void) | undefined;
  /** Console HAUL ROUTES emphasis. */
  routeEmphasis?: boolean;
  /** Corridors of the selected truck's Twin-stamped route, drawn lighter. */
  highlightCorridorIds?: readonly string[];
}) {
  // Above the EXAGGERATED relief, so the extent is never buried by the landform.
  const extentElevation = grid.maxM * grid.verticalExaggeration + 60;

  /*
    MINECAST-03 — map controls.

    The buttons live in the DOM, the camera lives here. The shell records a request in
    view state; this effect applies it once per sequence number, through the SAME
    MapControls the mouse drives, so a button and a drag can never disagree about where
    the camera is. `invalidate` is required under `frameloop="demand"`: nothing redraws
    on its own.
  */
  const controls = useRef<MapControlsImpl | null>(null);
  const { camera, invalidate } = useThree();
  const applied = useRef(0);
  useEffect(() => {
    const request = cameraRequest;
    const ctl = controls.current;
    if (!request || !ctl || request.seq === applied.current) return;
    applied.current = request.seq;

    const [tx, ty, tz] = framing.target;
    const reach = Math.hypot(grid.widthM, grid.heightM);
    const zoomable = camera as { zoom: number; updateProjectionMatrix: () => void };

    switch (request.command) {
      case "FIT":
        camera.position.set(framing.position[0], framing.position[1], framing.position[2]);
        ctl.target.set(tx, ty, tz);
        zoomable.zoom = 1;
        break;
      case "ZOOM_IN":
        zoomable.zoom = Math.min(zoomable.zoom * 1.3, 12);
        break;
      case "ZOOM_OUT":
        zoomable.zoom = Math.max(zoomable.zoom / 1.3, 0.35);
        break;
      case "PLAN_VIEW":
        // Straight down, from just south of the target, so screen-up is NORTH (+z).
        camera.position.set(tx, reach * 0.9, tz - reach * 0.002);
        ctl.target.set(tx, ty, tz);
        break;
      case "OBLIQUE_VIEW":
        camera.position.set(framing.position[0], framing.position[1], framing.position[2]);
        ctl.target.set(tx, ty, tz);
        break;
    }
    zoomable.updateProjectionMatrix();
    ctl.update();
    invalidate();
  }, [cameraRequest, camera, framing, grid.widthM, grid.heightM, invalidate]);

  return (
    <>
      {/*
        Flat, even lighting from two directions. No shadows and nothing animated: a
        moving highlight on a static landform could be mistaken for a data change.
      */}
      <ambientLight intensity={0.6} />
      <directionalLight
        position={[grid.widthM, grid.maxM * grid.verticalExaggeration + 1400, grid.heightM * 0.4]}
        intensity={0.95}
      />
      <directionalLight
        position={[-grid.widthM * 0.4, grid.maxM * grid.verticalExaggeration + 800, -grid.heightM]}
        intensity={0.3}
      />

      {layerVisibility.TERRAIN ? <MineTerrain grid={grid} /> : null}

      <MineGeometryOverlay
        features={features}
        surfaces={surfaces}
        grid={grid}
        showPit={layerVisibility.PIT}
        showBenches={layerVisibility.BENCHES}
      />

      {/* Synthetic operational corridors. Two layers so roads and ramps toggle apart. */}
      <HaulRoadsLayer
        corridors={corridors}
        grid={grid}
        showHaulRoads={layerVisibility.HAUL_ROADS}
        showRamps={layerVisibility.RAMPS}
        showRouteLabels={layerVisibility.ROUTES || routeEmphasis}
        emphasis={routeEmphasis}
        highlightCorridorIds={highlightCorridorIds}
      />

      {/* Working area, ore stockpile, waste dump: tinted patches on the same landform. */}
      <MineZonesLayer zones={zones} grid={grid} visible={layerVisibility.MINE_ZONES} />

      {layerVisibility.PUBLISHED_EXTENT ? (
        <PublishedExtentOutline
          widthM={grid.widthM}
          heightM={grid.heightM}
          elevationM={extentElevation}
        />
      ) : null}

      {/*
        MINECAST-01: the Twin's trucks. Drawn from `position_scene` - the same canonical
        value the 2D consoles use - and only where the Twin actually placed one.
      */}
      <VehicleMarkers
        positions={vehiclePositions}
        vehicles={vehicles}
        grid={grid}
        visible={layerVisibility.VEHICLES}
        selectedVehicleId={selectedVehicleId}
        onSelect={onSelectVehicle}
      />

      {/*
        Pan / zoom / rotate around the site. The initial framing comes from
        `overviewFraming`; named camera modes are a later pass.
      */}
      <MapControls
        ref={controls}
        target={[framing.target[0], framing.target[1], framing.target[2]]}
        enableDamping
        dampingFactor={0.15}
        maxPolarAngle={Math.PI / 2.15}
      />
    </>
  );
}
