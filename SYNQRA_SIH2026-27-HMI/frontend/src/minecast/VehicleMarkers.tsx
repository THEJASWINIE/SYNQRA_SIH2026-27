/**
 * Vehicle markers — the Digital Twin's trucks, in the 3D scene (MINECAST-01).
 *
 * ==========================================================================
 *  EVERY MARKER HERE IS A DIGITAL TWIN DEMONSTRATION POSITION.
 *
 *  The coordinates come from the canonical Twin field `position_scene`, the SAME value
 *  the Control Room's 2D map draws, validated by the SAME shared validator
 *  (`state/vehiclePosition.drawableScenePose`). This file computes NO position, holds no
 *  fallback coordinate, and contains no vehicle id: it renders exactly what it is handed.
 *
 *  A marker is drawn ONLY for a position whose `drawableInScene` is true. Nothing is
 *  placed at the origin, nothing is placed "approximately", and a truck the Twin cannot
 *  place simply does not appear - the overlay says so in words instead.
 * ==========================================================================
 *
 * THE ONE FRAME MAPPING, STATED ONCE
 *
 *   SpatialPosition.x  (metres EAST of the extent's south-west corner)  -> three.js  X
 *   SpatialPosition.y  (metres NORTH of the same corner)                -> three.js  Z
 *   terrain elevation at (x, y) * verticalExaggeration                  -> three.js  Y
 *
 * That is an AXIS MAPPING, not a conversion: no scale factor, no offset and no rotation is
 * applied to the canonical numbers. `MineTerrain` builds its mesh with the identical
 * mapping, which is why a marker lands on the surface rather than beside it. The Y
 * multiplier is the scene's existing, disclosed vertical exaggeration - the same one the
 * terrain and the viewport caption already use.
 *
 * WebGL only, so not unit tested (M4D-C). The placement decision, the frame and the
 * provenance it renders are all asserted in `spatialPosition.test.ts` and
 * `minecastVehicles.test.ts`.
 */

import { Html } from "@react-three/drei";
import { useMemo } from "react";
import { BufferAttribute, BufferGeometry, Line, LineBasicMaterial } from "three";

import { type CalloutSlot, calloutSlots, SLOT_OFFSET } from "../state/calloutLayout";
import type { MineCastVehicle } from "./minecastProjection";
import type { SpatialPosition } from "./spatialPosition";
import type { HeightGrid } from "./terrainField";
import { VehicleCallout } from "./VehicleCallout";
import { vehicleSurfaceY } from "./vehiclePlacement";

/**
 * Distinct colours, assigned deterministically from the canonical id.
 *
 * No vehicle id appears in this file: a truck's colour is a hash of whatever id the Twin
 * supplied, so the same truck is the same colour on every run and a third vehicle would
 * get one without a code change. Colour is a convenience only - the label above each
 * marker is what actually identifies it, so the scene survives greyscale (NFR-008).
 */
const MARKER_PALETTE: readonly number[] = [0xf2a54a, 0x6aa9ff, 0x3ddc84, 0xc084fc];

function markerColour(canonicalVehicleId: string): number {
  let hash = 0;
  for (let i = 0; i < canonicalVehicleId.length; i += 1) {
    hash = (hash * 31 + canonicalVehicleId.charCodeAt(i)) >>> 0;
  }
  return MARKER_PALETTE[hash % MARKER_PALETTE.length] as number;
}

/** Metres. Sized against a ~3.2 km site so a truck reads clearly without dominating. */
// MINE-ROUTES-02: smaller than before so a truck sits ON a 30 m road rather than over it;
// still several pixels at the overview scale so it remains obvious.
const BODY_WIDTH_M = 34;
const BODY_HEIGHT_M = 22;
const BODY_LENGTH_M = 58;
const MAST_HEIGHT_M = 110;
/** How far above the mast the DOM label sits, in scene metres. */
const LABEL_OFFSET_M = 30;
/** The selection ring on the ground: inner/outer radius in metres. */
const RING_INNER_M = 60;
const RING_OUTER_M = 78;
/**
 * DIGITAL-TWIN-OPERATIONAL-FLOW-01: how far a de-collided callout hangs from its mast,
 * scene metres, sideways (x) and extra height (y). The MARKER never moves; only the
 * label anchor does, and a leader line joins them. Sideways is +x (east), which the
 * default oblique camera shows as roughly screen-right.
 */
const CALLOUT_SIDE_M = 1000;
const CALLOUT_RAISE_M = 400;
/**
 * Proximity for the 3D rule, scene metres. Wider than the plan's default: a 3D callout
 * is ~180 px wide, which at the overview zoom is ~850 m of ground, and the oblique
 * camera foreshortens north-south distance, so trucks well apart on the ground still
 * collide on screen. Still a fixed, camera-independent number.
 */
const CALLOUT_NEAR_3D_M = 2200;

function VehicleMarker({
  position,
  vehicle,
  grid,
  selected,
  onSelect,
  slot,
}: {
  position: SpatialPosition;
  /** The projected vehicle the callout reads its figures from. Null = no telemetry row. */
  vehicle: MineCastVehicle | null;
  grid: HeightGrid;
  /** View state from the shell's store; this file never decides what is selected. */
  selected: boolean;
  onSelect?: ((canonicalVehicleId: string) => void) | undefined;
  /** Callout slot from `calloutSlots` - label placement only, never the truck. */
  slot: CalloutSlot;
}) {
  const { x, y } = position;
  const offset = SLOT_OFFSET[slot];
  const anchor: readonly [number, number, number] = [
    offset.dx * CALLOUT_SIDE_M,
    MAST_HEIGHT_M + LABEL_OFFSET_M + offset.dy * CALLOUT_RAISE_M,
    0,
  ];
  // Leader from the mast tip to the de-collided anchor. Built only when the label moved.
  const leader = useMemo(() => {
    if (slot === "DEFAULT") return null;
    const geometry = new BufferGeometry();
    geometry.setAttribute(
      "position",
      new BufferAttribute(new Float32Array([0, MAST_HEIGHT_M, 0, anchor[0], anchor[1], anchor[2]]), 3),
    );
    return new Line(geometry, new LineBasicMaterial({ color: markerColour(position.canonicalVehicleId), transparent: true, opacity: 0.9 }));
  }, [slot, anchor[0], anchor[1], anchor[2], position.canonicalVehicleId]);

  // Guarded by the caller too; this keeps the component independently safe.
  if (x === null || y === null) return null;

  const colour = markerColour(position.canonicalVehicleId);
  // Same hue for the DOM label's edge, so label and marker read as one object.
  const labelColour = `#${colour.toString(16).padStart(6, "0")}`;

  // MINECAST-02: sit the underside on the sampled terrain plus the declared clearance.
  // The lookup and the constant live in `vehiclePlacement.ts`, where they are unit tested.
  const groundY = vehicleSurfaceY(grid, x, y);

  /*
    Heading, when the Twin supplied one.

    The canonical heading is measured in the scene frame (radians, counter-clockwise from
    +x / east). three.js rotates about Y clockwise when viewed from above, hence the
    negation - an axis convention, not an adjustment of the value. With no heading
    supplied the body simply keeps the scene's default orientation and the pointer is
    hidden, rather than pointing somewhere invented.
  */
  const hasHeading = position.headingRad !== null;
  const yaw = hasHeading ? -(position.headingRad as number) : 0;

  const select = (event: { stopPropagation: () => void }) => {
    event.stopPropagation();
    onSelect?.(position.canonicalVehicleId);
  };

  return (
    <group position={[x, groundY, y]}>
      {/*
        MINECAST-03: the selected truck wears a flat ring on the ground, like the
        selection halo on an operations map. View state only - it means "the operator is
        looking at this one", never an operational condition.
      */}
      {selected ? (
        <mesh position={[0, 1.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[RING_INNER_M, RING_OUTER_M, 48]} />
          <meshBasicMaterial color={colour} transparent opacity={0.55} depthWrite={false} />
        </mesh>
      ) : null}

      {/* Body. A simple block: identification matters here, fidelity does not. */}
      <group rotation={[0, yaw, 0]}>
        <mesh position={[0, BODY_HEIGHT_M / 2, 0]} onClick={select}>
          <boxGeometry args={[BODY_LENGTH_M, BODY_HEIGHT_M, BODY_WIDTH_M]} />
          <meshStandardMaterial color={colour} roughness={0.6} metalness={0.1} />
        </mesh>

        {/* Direction of travel, drawn ONLY when the Twin actually supplied a heading. */}
        {hasHeading ? (
          <mesh
            position={[BODY_LENGTH_M * 0.75, BODY_HEIGHT_M / 2, 0]}
            rotation={[0, 0, -Math.PI / 2]}
          >
            <coneGeometry args={[BODY_WIDTH_M * 0.42, BODY_LENGTH_M * 0.5, 4]} />
            <meshStandardMaterial color={colour} roughness={0.5} />
          </mesh>
        ) : null}
      </group>

      {/*
        A mast, so a truck parked in a pit or behind a bench is still findable from the
        overview camera. Without it the markers vanish into the relief at this site scale.
      */}
      <mesh position={[0, MAST_HEIGHT_M / 2, 0]}>
        <cylinderGeometry args={[2.5, 2.5, MAST_HEIGHT_M, 6]} />
        <meshStandardMaterial color={colour} transparent opacity={0.85} />
      </mesh>

      {/*
        The label identifies the truck AND says what kind of position put it there, so the
        3D view can never imply a measured location.

        DOM, not in-scene text, and deliberately: an SDF text mesh (drei `Text` /
        troika-three-text) built an atlas large enough to LOSE THE WEBGL CONTEXT on this
        hardware - the whole viewport went blank, which is far worse than an unlabelled
        marker. `Html` costs the GPU nothing, stays crisp at any zoom, and is readable in
        a screenshot. Verified in the browser at both target resolutions.
      */}
      {leader ? <primitive object={leader} /> : null}
      <Html
        position={[anchor[0], anchor[1], anchor[2]]}
        zIndexRange={[20, 0]}
        // The label must never swallow a drag intended for the camera.
        style={{ pointerEvents: "none" }}
      >
        {vehicle ? (
          <VehicleCallout
            vehicle={vehicle}
            position={position}
            accent={labelColour}
            compact={slot !== "DEFAULT" && !selected}
          />
        ) : (
          // A position without a telemetry row: still identified, still marked simulated.
          <span className="mc-marker-label" style={{ borderColor: labelColour }}>
            {position.displayId} · SIMULATION
          </span>
        )}
      </Html>
    </group>
  );
}

/**
 * Every truck the Twin has placed.
 *
 * Takes already-resolved spatial positions and draws the drawable ones. It does not
 * filter by vehicle id, does not sort, and does not invent a marker for a truck the Twin
 * left unplaced.
 */
export function VehicleMarkers({
  positions,
  vehicles,
  grid,
  visible = true,
  selectedVehicleId = null,
  onSelect,
}: {
  positions: readonly SpatialPosition[];
  /** The projected fleet, joined to positions by canonical id. Figures only; no coordinates. */
  vehicles: readonly MineCastVehicle[];
  grid: HeightGrid;
  visible?: boolean;
  /** The shell's selection, by canonical id. */
  selectedVehicleId?: string | null;
  /** Clicking a truck selects it through the shell's store - the one selection path. */
  onSelect?: ((canonicalVehicleId: string) => void) | undefined;
}) {
  const drawable = useMemo(
    () => positions.filter((position) => position.drawableInScene),
    [positions],
  );
  // Deterministic label slots for trucks that are close together (same rule as the plan).
  const slots = useMemo(
    () =>
      calloutSlots(
        drawable.map((p) => ({ id: p.canonicalVehicleId, x: p.x ?? 0, y: p.y ?? 0 })),
        CALLOUT_NEAR_3D_M,
      ),
    [drawable],
  );

  if (!visible || drawable.length === 0) return null;

  return (
    <group>
      {drawable.map((position) => (
        <VehicleMarker
          key={position.canonicalVehicleId}
          position={position}
          vehicle={
            vehicles.find((v) => v.canonicalVehicleId === position.canonicalVehicleId) ?? null
          }
          grid={grid}
          selected={position.canonicalVehicleId === selectedVehicleId}
          onSelect={onSelect}
          slot={slots.get(position.canonicalVehicleId) ?? "DEFAULT"}
        />
      ))}
    </group>
  );
}
