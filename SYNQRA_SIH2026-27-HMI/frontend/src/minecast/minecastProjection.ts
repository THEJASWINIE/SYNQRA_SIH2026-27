/**
 * Mine-Cast projection — the canonical Twin, reshaped for a spatial view.
 *
 * ==========================================================================
 *  MINE-CAST IS A VIEWER. IT OWNS NO STATE AND AUTHORS NO VALUE.
 *
 *      canonical Digital Twin
 *              |
 *          AppState                (ONE store, filled by ONE provider)
 *         /      |      \
 *  control   projectVehicle()   projectMineCast()
 *   room     (T01 / T02 consoles)   (this module)
 *
 *  Everything below is a SELECTOR over `AppState`. This module holds no state, caches
 *  nothing, opens no socket, issues no request, submits no command and writes nothing
 *  back. Mine-Cast cannot mutate the Twin because there is no path from here that could.
 * ==========================================================================
 *
 * WHAT IT REFUSES TO DO
 *
 * It never manufactures a latitude, a longitude, a GNSS fix, a V2V link, a V2I link, a
 * radio metric, a safe speed, a risk level or a piece of mine infrastructure. Every field
 * below is either a value the Twin supplied or an explicit UNAVAILABLE. A number nobody
 * measured is not rendered as a number, and never as 0 - `0 m/s` means "stopped", which is
 * a very different claim from "we do not know".
 *
 * DISPLAY LABELS ARE NOT IDENTITY
 *
 * The spatial view labels the trucks T01 and T02 because a floating map label has very
 * little room. The CANONICAL ids stay TRUCK_01 and TRUCK_02 and travel alongside on every
 * record, because those are what the firmware, the operator registry, the command gateway
 * and the Twin all agree on. Nothing is renamed; a short label is added.
 *
 * Pure and framework-free, so it is testable without a DOM (M4D-C).
 */

import type { AppState } from "../contracts/appState";
import type { PositionOdom, VehicleState } from "../contracts/domain";
import {
  type DataState,
  fieldDataState,
  UNAVAILABLE_LABEL,
  vehicleProvenanceLabel,
} from "../state/dataStatus";
import { DEPOSIT5_EXTENT, formatDms, type LonLat, type SiteExtent } from "../state/geoSite";
import { type LinkStatus, v2iLink, v2vLink } from "../vehicle/communication";
import { VEHICLE_IDS } from "../vehicle/vehicleConfig";
import { type DrawableScenePose, drawableScenePose } from "../state/vehiclePosition";
import { peerOf, projectVehicle } from "../vehicle/vehicleProjection";

// ---------------------------------------------------------------------------
// display labels
// ---------------------------------------------------------------------------

/**
 * Short spatial labels. A map marker has room for three characters, not nine.
 *
 * This is a PRESENTATION map and nothing else. `canonicalVehicleId` is carried on every
 * projected vehicle so no consumer ever has to reverse this lookup, and so a label can
 * never be mistaken for an id the backend would accept.
 */
export const DISPLAY_LABELS: Readonly<Record<string, string>> = {
  TRUCK_01: "T01",
  TRUCK_02: "T02",
};

/**
 * The short label for a vehicle.
 *
 * Falls back to the canonical id rather than inventing an abbreviation: an unlabelled
 * third vehicle should read as its real name, not as a guess.
 */
export function displayLabelFor(canonicalVehicleId: string): string {
  return DISPLAY_LABELS[canonicalVehicleId] ?? canonicalVehicleId;
}

// ---------------------------------------------------------------------------
// provenance vocabulary
// ---------------------------------------------------------------------------

/**
 * Where a projected value came from. The distinctions here are the whole point of the
 * panel that renders them.
 *
 *   HARDWARE            a sensor measured it
 *   DERIVED             computed from a measurement, by a named method
 *   SOFTWARE_TEST       produced by a test harness (synthetic GNSS, emulator)
 *   SYNTHETIC_FOR_DEMO  invented for demonstration; not a measurement of anything
 *   SIMULATION          produced by the simulation provider
 *   REPLAY              recorded earlier; historical, not current
 *   UNAVAILABLE         nothing supplied it
 *
 * SYNTHETIC_FOR_DEMO and SOFTWARE_TEST are never collapsed into HARDWARE or DERIVED, and
 * there is deliberately no function anywhere in this module that promotes one to another.
 */
export type MineCastProvenance =
  | "HARDWARE"
  | "DERIVED"
  | "SOFTWARE_TEST"
  | "SYNTHETIC_FOR_DEMO"
  | "SIMULATION"
  | "REPLAY"
  | "UNAVAILABLE";

export const PROVENANCE_TEXT: Record<MineCastProvenance, string> = {
  HARDWARE: "PHYSICAL — measured by a sensor",
  DERIVED: "PHYSICAL_DERIVED — computed from a measurement",
  SOFTWARE_TEST: "SOFTWARE TEST — produced by a test harness",
  SYNTHETIC_FOR_DEMO: "SYNTHETIC_FOR_DEMO — invented for demonstration",
  SIMULATION: "SIMULATION — produced by the simulation provider",
  REPLAY: "REPLAY — recorded earlier, not current",
  UNAVAILABLE: "UNAVAILABLE — nothing supplied it",
};

// ---------------------------------------------------------------------------
// position
// ---------------------------------------------------------------------------

/**
 * The kind of position a vehicle has, if it has one at all.
 *
 * GEOGRAPHIC and LOCAL_ODOMETRY are kept apart on purpose. A local odometry pose is an
 * (x, y) in metres from a configured start point with an accumulating error; it is NOT a
 * coordinate on the earth, and converting one into the other without a surveyed anchor
 * would invent precision this prototype does not have.
 */
export type MineCastPositionKind = "GEOGRAPHIC" | "LOCAL_ODOMETRY" | "UNAVAILABLE";

export interface MineCastPosition {
  readonly kind: MineCastPositionKind;
  /** True only when a position genuinely exists and may be drawn. */
  readonly available: boolean;
  readonly provenance: MineCastProvenance;
  /** The estimator that produced it, when one did. Never "GNSS" for odometry. */
  readonly method: string;
  /** Local-frame metres. Null for anything that is not a local odometry pose. */
  readonly xM: number | null;
  readonly yM: number | null;
  /**
   * The geographic coordinate, ONLY for `kind === "GEOGRAPHIC"`.
   *
   * Null for a local odometry pose, and there is no branch anywhere that fills it from
   * one: a pose in metres from a configured origin has no coordinate on the earth, and
   * synthesising one would be the exact fabrication this projection exists to prevent.
   * Carried so `spatialPosition.ts` can apply an established projection to a real fix.
   */
  readonly lonLat: LonLat | null;
  readonly headingRad: number | null;
  readonly distanceM: number | null;
  /** Why a position is absent or degraded, stated rather than implied. */
  readonly reason: string;
  /**
   * Freshness of the pose, from the Twin's own stamp.
   *
   * A pose that has stopped updating is STALE, and stale is not a position you may steer
   * by. It is never silently held forward as current.
   */
  readonly dataState: DataState;
}

const NO_POSITION: MineCastPosition = {
  kind: "UNAVAILABLE",
  available: false,
  provenance: "UNAVAILABLE",
  method: "NONE",
  xM: null,
  yM: null,
  lonLat: null,
  headingRad: null,
  distanceM: null,
  reason:
    "No positioning source supplied for this vehicle. No GNSS receiver is fitted, and no local pose was produced.",
  dataState: "UNAVAILABLE",
};

/** Map the odometry adapter's own provenance words onto the Mine-Cast vocabulary. */
function odomProvenance(odom: PositionOdom): MineCastProvenance {
  const label = odom.provenanceLabel.toUpperCase();
  if (label.includes("PHYSICAL_DERIVED")) return "DERIVED";
  if (label.includes("SYNTHETIC")) return "SYNTHETIC_FOR_DEMO";
  if (label.includes("SOFTWARE")) return "SOFTWARE_TEST";
  if (label.includes("SIMULAT")) return "SIMULATION";
  if (label.includes("REPLAY")) return "REPLAY";
  // Unrecognised wording is UNAVAILABLE, never HARDWARE. An unknown label is not evidence.
  return "UNAVAILABLE";
}

/**
 * The vehicle's position, as the Twin actually supplied it.
 *
 * Order matters and is deliberate. A LOCAL ODOMETRY pose is reported as exactly that; it
 * is never widened into a geographic fix. A GNSS fix is only reported when the Twin
 * carries one, and a synthetic fix keeps its synthetic provenance all the way to the
 * screen.
 */
export function positionOf(vehicle: VehicleState | null): MineCastPosition {
  if (!vehicle) return NO_POSITION;

  // -- local odometry (TRUCK_01 wheel + IMU) -------------------------------
  const odom = vehicle.positionOdom ?? null;
  if (odom && odom.status.toUpperCase() === "VALID" && odom.xM !== null && odom.yM !== null) {
    return {
      kind: "LOCAL_ODOMETRY",
      available: true,
      provenance: odomProvenance(odom),
      method: odom.method,
      xM: odom.xM,
      yM: odom.yM,
      // A local pose has no coordinate on the earth. Permanently null here.
      lonLat: null,
      headingRad: odom.headingRad,
      distanceM: odom.distanceM,
      reason:
        odom.reason ??
        "Local odometry pose in metres from a configured origin. NOT a geographic coordinate.",
      dataState: fieldDataState(vehicle.provenance?.position_odom),
    };
  }

  // -- GNSS, when the Twin carries a fix -----------------------------------
  const gnss = vehicle.positionGnss ?? null;
  const fixed =
    gnss &&
    typeof gnss.latitude === "number" &&
    Number.isFinite(gnss.latitude) &&
    typeof gnss.longitude === "number" &&
    Number.isFinite(gnss.longitude);

  if (gnss && fixed) {
    const origin = (gnss.origin ?? vehicle.provenance?.position_gnss?.origin ?? "")
      .toString()
      .toUpperCase();
    const synthetic =
      origin.includes("SOFTWARE_ONLY") ||
      origin.includes("SYNTHETIC") ||
      origin.includes("SIMULAT");
    return {
      kind: "GEOGRAPHIC",
      available: true,
      // A synthetic fix stays SOFTWARE_TEST. There is no branch that makes it HARDWARE.
      provenance: synthetic ? "SOFTWARE_TEST" : "HARDWARE",
      method: synthetic ? "SYNTHETIC_GNSS" : "GNSS",
      xM: null,
      yM: null,
      lonLat: { lon: gnss.longitude as number, lat: gnss.latitude as number },
      headingRad: null,
      distanceM: null,
      reason: synthetic
        ? "SOFTWARE TEST · SYNTHETIC GNSS. Not a measurement of any physical vehicle."
        : "Physical GNSS fix.",
      dataState: fieldDataState(vehicle.provenance?.position_gnss),
    };
  }

  // -- odometry that exists but is not valid -------------------------------
  if (odom) {
    return {
      ...NO_POSITION,
      method: odom.method,
      reason:
        odom.reason ??
        `Local odometry reported status ${odom.status}; no usable pose. Position remains unavailable.`,
    };
  }

  return NO_POSITION;
}

// ---------------------------------------------------------------------------
// vehicles
// ---------------------------------------------------------------------------

/** Whether the view can trust this vehicle's data right now. */
export type MineCastAvailability = "AVAILABLE" | "DEGRADED" | "UNAVAILABLE";

export interface MineCastSafety {
  /** m/s, as supplied. Null is UNAVAILABLE and is never rendered as 0. */
  readonly actualSpeedMps: number | null;
  readonly vSafeMps: number | null;
  readonly hSafeM: number | null;
  readonly headwayM: number | null;
  readonly leadVehicleId: string | null;
  readonly riskLevel: string | null;
  readonly activeConstraint: string | null;
  readonly headwayViolation: boolean | null;
  readonly envelopeViolation: boolean | null;
  /** True when the safety subsystem supplied nothing at all for this vehicle. */
  readonly unavailable: boolean;
}

export interface MineCastVehicle {
  /** What the backend, firmware and Twin call this vehicle. Authoritative. */
  readonly canonicalVehicleId: string;
  /** Short spatial label. Presentation only — never sent anywhere. */
  readonly displayId: string;

  readonly present: boolean;
  readonly availability: MineCastAvailability;
  readonly dataState: DataState;
  /** Provenance of the vehicle's own telemetry, from the shared helper. */
  readonly dataSource: string;

  readonly speedMps: number | null;
  readonly mode: string | null;

  readonly position: MineCastPosition;
  /**
   * MINECAST-01 — the canonical Digital Twin DEMONSTRATION pose, when the Twin carries one.
   *
   * Kept in its own field rather than folded into `position` on purpose: they answer
   * different questions and must not displace each other. `position` reports what the
   * vehicle's own instruments produced (a local odometry pose, or nothing). `scenePose`
   * reports where the Digital Twin is placing this truck in the demonstration scene.
   *
   * It is the SAME `position_scene` value the Control Room's 2D map draws, validated by
   * the SAME shared validator - there is no second source of truth and no Mine-Cast-only
   * coordinate anywhere.
   */
  readonly scenePose: DrawableScenePose | null;
  readonly safety: MineCastSafety;

  /** The three links, each computed from evidence by the shared communication module. */
  readonly v2v: LinkStatus;
  readonly v2i: LinkStatus;

  /** The other truck's canonical id, when there is exactly one. */
  readonly peerVehicleId: string | null;
  /** The peer's short label, when a peer exists. */
  readonly peerDisplayId: string | null;
  /**
   * True only when the peer is genuinely present in the Twin.
   *
   * Peer PRESENCE is not a communication claim: two trucks both reporting to the backend
   * over Wi-Fi says nothing about whether they can hear each other over LoRa. That
   * question is answered by `v2v`, from measured evidence, and nowhere else.
   */
  readonly peerPresent: boolean;

  readonly alertCount: number;
  readonly activeAlertCount: number;
}

function safetyOf(projected: ReturnType<typeof projectVehicle>): MineCastSafety {
  const safety = projected.safety;
  if (!safety) {
    return {
      actualSpeedMps: null,
      vSafeMps: null,
      hSafeM: null,
      headwayM: null,
      leadVehicleId: null,
      riskLevel: null,
      activeConstraint: null,
      headwayViolation: null,
      envelopeViolation: null,
      unavailable: true,
    };
  }

  return {
    // `actualSpeed` is non-null on the contract; the vehicle's own speed is the fallback.
    actualSpeedMps: safety.actualSpeed ?? projected.vehicle?.speedMps ?? null,
    vSafeMps: safety.vSafe,
    hSafeM: safety.hSafe,
    headwayM: safety.headwayCurrent,
    leadVehicleId: safety.leadVehicleId,
    riskLevel: safety.riskLevel,
    activeConstraint: safety.activeConstraint,
    headwayViolation: safety.headwayViolation,
    envelopeViolation: safety.envelopeViolation,
    unavailable: false,
  };
}

/**
 * Availability, from freshness and presence only.
 *
 * A vehicle the Twin does not carry is UNAVAILABLE. One whose telemetry has gone stale is
 * DEGRADED, not AVAILABLE - the last value is still shown, but it is never presented as
 * current. UNKNOWN freshness (the staleness threshold is unconfigured, AMB-014) counts as
 * AVAILABLE with the UNKNOWN data state carried alongside, matching the rest of the HMI.
 */
function availabilityOf(present: boolean, dataState: DataState): MineCastAvailability {
  if (!present) return "UNAVAILABLE";
  switch (dataState) {
    case "CURRENT":
    case "UNKNOWN":
      return "AVAILABLE";
    case "STALE":
      return "DEGRADED";
    case "UNAVAILABLE":
      return "UNAVAILABLE";
  }
}

/**
 * Project one vehicle for the spatial view.
 *
 * Built on top of `projectVehicle`, the SAME isolation boundary the T01 and T02 consoles
 * use, so the two cannot drift apart about which data belongs to which truck. Nothing
 * here reaches into `state.vehicles` directly.
 */
export function projectMineCastVehicle(
  state: AppState,
  canonicalVehicleId: string,
  mode: string,
): MineCastVehicle {
  const projected = projectVehicle(state, canonicalVehicleId);
  const vehicle = projected.vehicle;

  const stamped =
    vehicle?.provenance?.received_at ?? vehicle?.provenance?.rpm ?? vehicle?.provenance?.speed_mps;
  const dataState = fieldDataState(stamped);

  const peerVehicleId = peerOf(canonicalVehicleId);

  return {
    canonicalVehicleId,
    displayId: displayLabelFor(canonicalVehicleId),

    present: projected.present,
    availability: availabilityOf(projected.present, dataState),
    dataState,
    dataSource: vehicleProvenanceLabel(vehicle),

    speedMps: vehicle?.speedMps ?? null,
    mode: vehicle?.mode ?? null,

    position: positionOf(vehicle),
    // MINECAST-01: the canonical demo pose, through the shared validator. Mine-Cast
    // computes no coordinate of its own and holds no fallback for a missing one.
    scenePose: vehicle ? drawableScenePose(vehicle) : null,
    safety: safetyOf(projected),

    // Both links come from the shared, already-verified communication module. Mine-Cast
    // does not re-derive link state and cannot reach a different answer than the consoles.
    v2v: v2vLink(vehicle),
    v2i: v2iLink(mode),

    peerVehicleId,
    peerDisplayId: peerVehicleId ? displayLabelFor(peerVehicleId) : null,
    peerPresent: projected.peer !== null,

    alertCount: projected.alerts.length,
    activeAlertCount: projected.alerts.filter((alert) => alert.active).length,
  };
}

// ---------------------------------------------------------------------------
// site
// ---------------------------------------------------------------------------

/**
 * The site context Mine-Cast may legitimately draw.
 *
 * `extent` is the PUBLISHED COORDINATE EXTENT: four coordinate extrema taken from a
 * government Environmental Clearance document. It is NOT a surveyed lease boundary, NOT a
 * cadastral polygon and NOT a pillar list, and the label travels with the data so no
 * renderer can quietly drop the caveat.
 */
export interface MineCastSite {
  readonly name: string;
  readonly operator: string;
  readonly district: string;
  readonly state: string;
  readonly extent: SiteExtent;
  /** Rendered on every view of the extent. Not optional, not a tooltip. */
  readonly extentLabel: string;
  readonly extentCaveat: string;
  /** The datum has not been verified from the source document. */
  readonly coordinateReference: "ASSUMED_WGS84_UNVERIFIED";
  readonly publishedAreaHa: number;
  readonly sourceFileNo: string;
  readonly sourceDescription: string;
}

export const EXTENT_LABEL = "PUBLISHED COORDINATE EXTENT";
export const EXTENT_CAVEAT = "NOT A LEASE BOUNDARY";

export const MINECAST_SITE: MineCastSite = {
  name: "Bailadila Iron Ore Mine, Deposit-5",
  operator: "NMDC Limited",
  district: "Bacheli, South Bastar Dantewada",
  state: "Chhattisgarh, India",
  extent: DEPOSIT5_EXTENT,
  extentLabel: EXTENT_LABEL,
  extentCaveat: EXTENT_CAVEAT,
  coordinateReference: "ASSUMED_WGS84_UNVERIFIED",
  publishedAreaHa: 540.05,
  sourceFileNo: "J-11015/261/2007-IA.II(M)",
  sourceDescription:
    "Government of India, Ministry of Environment, Forest and Climate Change — Environmental Clearance, 11/12/2024.",
};

/** The extent as four human-readable DMS strings, for the mini-map and provenance panel. */
export function extentText(site: MineCastSite = MINECAST_SITE): {
  north: string;
  south: string;
  east: string;
  west: string;
} {
  return {
    north: formatDms(site.extent.north),
    south: formatDms(site.extent.south),
    east: formatDms(site.extent.east),
    west: formatDms(site.extent.west),
  };
}

// ---------------------------------------------------------------------------
// layers
// ---------------------------------------------------------------------------

/**
 * The layer catalogue.
 *
 * Every entry declares whether it is IMPLEMENTED. Pass 1 implements none of the spatial
 * layers, so the drawer shows them as NOT BUILT rather than as switches that appear to do
 * something. A toggle that silently does nothing is worse than an honest disabled row: it
 * teaches an operator that a layer is on when nothing is being drawn.
 */
export type LayerId =
  | "TERRAIN"
  | "ORTHOPHOTO"
  | "PUBLISHED_EXTENT"
  | "PIT"
  | "BENCHES"
  | "HAUL_ROADS"
  | "RAMPS"
  | "MINE_ZONES"
  | "VEHICLES"
  | "ROUTES"
  | "SAFETY"
  | "V2V"
  | "V2I_RSU";

export interface LayerDescriptor {
  readonly id: LayerId;
  readonly label: string;
  /** Whether any renderer exists for this layer yet. False for every spatial layer in Pass 1. */
  readonly implemented: boolean;
  /** Default visibility once implemented. */
  readonly defaultVisible: boolean;
  /** What the layer would draw, and where that geometry would come from. */
  readonly provenance: MineCastProvenance;
  readonly note: string;
}

const NOT_BUILT = "No renderer exists yet. This control sets view state only.";

/** Drawn by the spatial scene. The toggle genuinely shows and hides geometry. */
const DRAWN = "Rendered by the spatial view.";

export const LAYERS: readonly LayerDescriptor[] = [
  {
    id: "TERRAIN",
    label: "Terrain",
    implemented: true,
    defaultVisible: true,
    provenance: "SYNTHETIC_FOR_DEMO",
    note: `${DRAWN} No DEM is bundled, so the surface is procedurally generated and is NOT a survey of Deposit-5.`,
  },
  {
    id: "ORTHOPHOTO",
    label: "Orthophoto",
    implemented: false,
    defaultVisible: false,
    provenance: "UNAVAILABLE",
    note: `${NOT_BUILT} No imagery is bundled or licensed for this site.`,
  },
  {
    id: "PUBLISHED_EXTENT",
    label: "Published Extent",
    implemented: true,
    defaultVisible: true,
    provenance: "HARDWARE",
    note: `${DRAWN} Four published coordinate extrema, drawn dashed. ${EXTENT_LABEL} — ${EXTENT_CAVEAT}.`,
  },
  {
    id: "PIT",
    label: "Pit",
    implemented: true,
    defaultVisible: true,
    provenance: "SYNTHETIC_FOR_DEMO",
    note: `${DRAWN} Invented pit outline. No authoritative pit survey exists in this repository.`,
  },
  {
    id: "BENCHES",
    label: "Benches",
    implemented: true,
    defaultVisible: true,
    provenance: "SYNTHETIC_FOR_DEMO",
    note: `${DRAWN} Invented bench shelves and faces. No authoritative bench survey exists in this repository.`,
  },
  {
    id: "HAUL_ROADS",
    label: "Haul Roads",
    implemented: true,
    defaultVisible: true,
    provenance: "SYNTHETIC_FOR_DEMO",
    note: `${DRAWN} Synthetic operational corridors — NOT NMDC infrastructure. No surveyed Deposit-5 road geometry exists in this repository.`,
  },
  {
    id: "RAMPS",
    label: "Ramps",
    implemented: true,
    defaultVisible: true,
    provenance: "SYNTHETIC_FOR_DEMO",
    note: `${DRAWN} Synthetic pit ramp — NOT NMDC infrastructure. Draped on the synthetic terrain's own bench steps.`,
  },
  {
    id: "MINE_ZONES",
    label: "Mine Zones",
    implemented: true,
    defaultVisible: true,
    provenance: "SYNTHETIC_FOR_DEMO",
    note: `${DRAWN} Active working area, ore stockpile and terraced waste dump, invented for demonstration. Not surveyed, NOT NMDC infrastructure.`,
  },
  {
    id: "VEHICLES",
    label: "Vehicles",
    implemented: true,
    defaultVisible: true,
    // The MARKERS are Digital Twin demonstration placements, not measurements. The
    // provenance a reader sees must describe the position that put the truck there.
    provenance: "SIMULATION",
    note: `${DRAWN} Drawn from the canonical Twin's SCENE_METRES demonstration position - the same value the 2D consoles use. Never a GNSS fix, and a marker appears only where the Twin placed one.`,
  },
  {
    id: "ROUTES",
    label: "Routes",
    implemented: true,
    defaultVisible: false,
    provenance: "SYNTHETIC_FOR_DEMO",
    note: `${DRAWN} Engineering labels on the synthetic corridors (MAIN HAUL, PIT RAMP 01 ...). SYNTHETIC_DIGITAL_TWIN_ROUTE - invented names, not official ones.`,
  },
  {
    id: "SAFETY",
    label: "Safety",
    implemented: false,
    defaultVisible: true,
    provenance: "DERIVED",
    note: `${NOT_BUILT} Safety semantics come from the Twin; none are computed here.`,
  },
  {
    id: "V2V",
    label: "V2V",
    implemented: false,
    defaultVisible: true,
    provenance: "UNAVAILABLE",
    note: `${NOT_BUILT} A link is drawn only from measured LoRa evidence.`,
  },
  {
    id: "V2I_RSU",
    label: "V2I / RSU",
    implemented: false,
    defaultVisible: false,
    provenance: "UNAVAILABLE",
    note: `${NOT_BUILT} No physical roadside unit exists on this prototype.`,
  },
];

// ---------------------------------------------------------------------------
// the whole view
// ---------------------------------------------------------------------------

/** How the operator should read what is on screen. */
export type MineCastFeedState = "LIVE" | "DEGRADED" | "REPLAY" | "OFFLINE";

export interface MineCastState {
  readonly site: MineCastSite;
  /** LIVE / DEGRADED / REPLAY / OFFLINE. Never LIVE while the feed is stale or down. */
  readonly feedState: MineCastFeedState;
  /** The provider actually driving the store: LIVE / MOCK / REPLAY. */
  readonly mode: string;
  readonly connectionStatus: string;
  readonly connectionError: string | null;
  readonly scenarioName: string | null;
  readonly observedAtIso: string | null;

  readonly vehicles: readonly MineCastVehicle[];
  readonly fleetTotal: number;
  readonly fleetAvailable: number;
  readonly fleetDegraded: number;
  readonly fleetUnavailable: number;
  /** Vehicles the view can actually place. Zero is the honest answer with no positioning. */
  readonly placeableCount: number;
  readonly activeAlertCount: number;

  readonly layers: readonly LayerDescriptor[];
  /** True while no vehicle position on screen came from physical hardware. */
  readonly noPhysicalPositioning: boolean;
}

/**
 * Feed state, from the provider and the fleet's freshness.
 *
 * REPLAY wins outright: a recording must never be labelled LIVE. A live provider whose
 * data has gone stale, or which carries no vehicle at all, is DEGRADED - never LIVE.
 */
function feedStateOf(
  connectionStatus: string,
  provider: string,
  vehicles: readonly MineCastVehicle[],
): MineCastFeedState {
  if (provider === "REPLAY") return "REPLAY";

  const status = connectionStatus.toUpperCase();
  if (status === "DISCONNECTED" || status === "ERROR" || status === "CLOSED") return "OFFLINE";

  const anyAvailable = vehicles.some((vehicle) => vehicle.availability === "AVAILABLE");
  if (!anyAvailable) return "DEGRADED";

  const anyDegraded = vehicles.some((vehicle) => vehicle.availability !== "AVAILABLE");
  return anyDegraded ? "DEGRADED" : "LIVE";
}

/**
 * Project the whole canonical state for the spatial view.
 *
 * The fleet is enumerated from the CONFIGURED vehicle list, not from whatever keys happen
 * to be in the store. A truck that has stopped reporting must still appear, as
 * UNAVAILABLE - a vehicle vanishing off the map is exactly the failure an operator must
 * never be shown.
 */
export function projectMineCast(state: AppState): MineCastState {
  const mode = state.connection.provider;

  const vehicles = VEHICLE_IDS.map((id) => projectMineCastVehicle(state, id, mode));

  const fleetAvailable = vehicles.filter((v) => v.availability === "AVAILABLE").length;
  const fleetDegraded = vehicles.filter((v) => v.availability === "DEGRADED").length;
  const fleetUnavailable = vehicles.filter((v) => v.availability === "UNAVAILABLE").length;

  return {
    site: MINECAST_SITE,
    feedState: feedStateOf(state.connection.status, mode, vehicles),
    mode,
    connectionStatus: state.connection.status,
    connectionError: state.connection.error,
    scenarioName: state.connection.scenarioName,
    observedAtIso: state.connection.lastMessageAt,

    vehicles,
    fleetTotal: vehicles.length,
    fleetAvailable,
    fleetDegraded,
    fleetUnavailable,
    // MINECAST-01: what can actually be DRAWN, which now includes the Twin's demo scene
    // poses. Whether any of it is a MEASUREMENT is a separate question, answered by
    // `noPhysicalPositioning` below and stated wherever this count is shown.
    placeableCount: vehicles.filter((v) => v.position.available || v.scenePose !== null).length,
    activeAlertCount: vehicles.reduce((sum, v) => sum + v.activeAlertCount, 0),

    layers: LAYERS,
    noPhysicalPositioning: vehicles.every((v) => v.position.provenance !== "HARDWARE"),
  };
}

/** Format a supplied speed, or the unavailable label. Never 0 for "unknown". */
export function speedText(mps: number | null): string {
  return mps === null || !Number.isFinite(mps) ? UNAVAILABLE_LABEL : `${mps.toFixed(1)} m/s`;
}

/** Format a supplied distance in metres, or the unavailable label. */
export function metresText(m: number | null): string {
  return m === null || !Number.isFinite(m) ? UNAVAILABLE_LABEL : `${m.toFixed(1)} m`;
}
