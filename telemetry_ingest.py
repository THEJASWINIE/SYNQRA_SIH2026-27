"""
FOG-ORCHESTRATOR 2.0 — Canonical Telemetry Ingestion Boundary (P3).

    ESP32 / emulator / gateway
            |
            v
    transport-specific parser        (EXISTING, reused - not reimplemented)
      v2v_packet_parser.V2VPacketParser              "STATE,TRUCK_0x,seq,rpm,speed,ax..gz"
      gateway_serial_reader.GatewayTelemetryParser   "V=TRUCK_01,SEQ=..,RPM=.."
      HMI POST /api/hardware/telemetry               JSON body
            |
            v
    NormalizedTelemetry              (this module - THE single boundary)
            |
            v
    validate -> dedup/order -> provenance -> quality
            |
            v
    TwinStateStore.update_vehicle_fields(...)   ATOMIC
            |
            v
    canonical Twin state

This module adds NO new wire format and NO fourth parser. It normalizes what the three
existing parsers already produce, decides provenance, and performs the only write into
the canonical Twin.

WHAT IT REFUSES TO DO
  - fabricate position, heading, road_id, visibility or friction as hardware observations
  - label a synthetic or emulated packet HARDWARE
  - present a PWM-derived speed as an encoder measurement
  - mutate the Twin before validation, dedup and ordering have passed
  - crash a server because one packet was malformed
"""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from integration_adapters.unit_converter import UnitConverter
from integration_adapters.vehicle_id_mapper import VehicleIDMapper
from integration_adapters.wheel_imu_odometry import WheelImuOdometryCalculator

logger = logging.getLogger("TelemetryIngest")


# =====================================================================
# HARDWARE TRUTH TABLE
# =====================================================================
#
# Documented facts about the EXISTING prototype firmware. These are observations of what
# the hardware actually reports, not tuning parameters.
#
#   Wheel RPM        MEASURED. LM393 slot sensor + ISR pulse count.
#                    esp32_code/VEHICLE_A_HMI_FIRMWARE.ino:128
#                    wheelRPM = (pulsesPerSecond / PULSES_PER_REV) * 60.0
#
#   TRUCK_01 speed   DERIVED FROM MEASUREMENT. speedMps = RPM * pi * D / 60
#                    esp32_code/VEHICLE_A_HMI_FIRMWARE.ino:129
#
#   TRUCK_02 speed   SYNTHETIC / PWM-DERIVED. The firmware places the Digital-Twin
#                    commanded prototype velocity into the V2V SPEED field:
#                    appliedSpeedMs = (appliedMotorPWM / MAX_MOTOR_PWM) * MAX_PROTOTYPE_SPEED_MS
#                    esp32_code/VEHICLE_B_TRUCK_02_V2V_DIGITAL_TWIN_MOTOR/...ino
#                    with the firmware's own comment: "the V2V SPEED FIELD carries the
#                    Digital-Twin-controlled prototype velocity ... even if the encoder is
#                    not generating pulses."
#                    It MUST NOT be represented as an encoder-measured speed.
#
#   IMU              MEASURED. Raw MPU6050 LSB, converted to SI by the existing parsers.
#
#   position/heading/road_id/visibility/friction
#                    NOT MEASURED BY ANY SENSOR ON THIS PROTOTYPE. Never populated here.
#
# Vehicles whose reported SPEED field is PWM-derived rather than encoder-measured.
PWM_DERIVED_SPEED_VEHICLES = frozenset({"TRUCK_02"})

# Fields no sensor on this prototype produces. Listed explicitly so that a future edit
# populating one of them from a telemetry packet is an obvious mistake.
NEVER_FROM_HARDWARE = frozenset(
    {
        "position_s",
        "road_id",
        "node_id",
        "heading_rad",
        "visibility_m",
        "friction_mu",
        # A geographic fix is a measurement like any other, and no sensor on this
        # prototype produces one. Listed here so the same guard that protects the
        # others protects the coordinate too - see GNSS_EQUIPPED_VEHICLES.
        "position_gnss",
    }
)

# Vehicles carrying a VERIFIED physical GNSS receiver.
#
# EMPTY, and that is the hardware truth: no vehicle on this prototype has one. The
# firmware sends no latitude or longitude at all.
#
# This is the ONLY way a coordinate can be stamped HARDWARE. Everything else - an
# omitted simulation flag, a "position_source": "GNSS" tag, arrival on the
# physical-device transport - is a CLIENT CLAIM, and a claim is not evidence. Before
# this allowlist existed, any unauthenticated caller that posted a latitude and a
# longitude to the hardware ingress got a position stamped HARDWARE, which the HMI
# then drew as a physical GNSS fix.
#
# Fitting a real receiver is a one-line change here, backed by physical evidence.
GNSS_EQUIPPED_VEHICLES: frozenset = frozenset()

# D006: Maximum number of recent sequence numbers tracked per vehicle for
# duplicate detection. The ordering decision uses last_accepted_sequence
# (one int per vehicle) and is unaffected by this limit.
MAX_DEDUP_HISTORY = 1000


class BoundedSequenceTracker:
    """O(1) membership check with bounded memory, for duplicate detection only.

    Ordering is decided by last_accepted_sequence, NOT by the contents of this
    tracker.  When a sequence falls out of the deque, it is NOT reclassified as
    "new" — it is still rejected as out-of-order by the last_accepted_sequence
    comparison.
    """

    __slots__ = ("_deque", "_set", "_maxlen")

    def __init__(self, maxlen: int = MAX_DEDUP_HISTORY):
        self._deque: deque = deque(maxlen=maxlen)
        self._set: set = set()
        self._maxlen = maxlen

    def add(self, seq: int) -> None:
        if len(self._deque) == self._maxlen:
            evicted = self._deque[0]
            self._set.discard(evicted)
        self._deque.append(seq)
        self._set.add(seq)

    def __contains__(self, seq: int) -> bool:
        return seq in self._set

    def __len__(self) -> int:
        return len(self._set)

    def __iter__(self):
        return iter(self._set)

    def clear(self) -> None:
        self._deque.clear()
        self._set.clear()


# =====================================================================
# TRANSPORT / PROVENANCE
# =====================================================================

class Transport:
    """How a packet reached us. Distinct from provenance."""

    V2V = "V2V"                        # LoRa relay, frozen STATE,... packet
    DIRECT_WIFI = "DIRECT_WIFI"        # ESP32 HTTP POST straight to the backend
    SERIAL_GATEWAY = "SERIAL_GATEWAY"  # LoRa gateway over USB serial
    EMULATOR = "EMULATOR"              # software emulator / replayed fixture

    ALL = frozenset({V2V, DIRECT_WIFI, SERIAL_GATEWAY, EMULATOR})


# Quality vocabulary of the EXISTING TelemetryQualityFilter / parsers, mapped onto the
# Twin's vocabulary. No new quality information is invented here.
_QUALITY_MAP = {
    "LIVE": "GOOD",
    "OK": "GOOD",
    "ONLINE": "GOOD",
    "DELAYED": "DEGRADED",
    "RECOVERING": "DEGRADED",
    "NOT_CALIBRATED": "DEGRADED",
    "STALE": "STALE",
    "OFFLINE": "STALE",
    "INVALID": "INVALID",
    "CORRUPTED": "INVALID",
}


def map_quality(raw: Optional[str]):
    """Translate an existing parser/filter quality label into the Twin vocabulary."""
    from twin.twin_state_store import Quality

    if raw is None:
        return Quality.UNKNOWN
    return Quality(_QUALITY_MAP.get(str(raw).upper(), "UNKNOWN"))


# =====================================================================
# NORMALIZED TELEMETRY  (the single representation)
# =====================================================================

@dataclass
class NormalizedTelemetry:
    """
    One telemetry observation, transport-agnostic.

    Optional hardware signals default to None. A None field means NOT REPORTED and is
    never written to the Twin, so it stays UNAVAILABLE rather than becoming a fabricated
    zero.
    """

    vehicle_id: str
    sequence: int
    received_at: float                      # when WE received it (never a measurement time)
    timestamp: Optional[float] = None       # source/measurement time, if the source gave one
    transport: str = Transport.EMULATOR
    is_simulated: bool = False              # True => provenance is SIMULATION, never HARDWARE

    rpm: Optional[float] = None
    speed_mps: Optional[float] = None            # only when genuinely encoder-derived
    speed_mps_reported: Optional[float] = None   # whatever the packet's SPEED field carried
    ax_mps2: Optional[float] = None
    ay_mps2: Optional[float] = None
    az_mps2: Optional[float] = None
    gx_rad_s: Optional[float] = None
    gy_rad_s: Optional[float] = None
    gz_rad_s: Optional[float] = None

    communication_state: Optional[str] = None
    raw_quality: Optional[str] = None
    rssi: Optional[float] = None
    snr: Optional[float] = None

    # Encoder pulse fields for physical local odometry (Pass 2)
    pulse_count: Optional[int] = None
    delta_pulses: Optional[int] = None

    # First-class GNSS position payload (Rules 1-12)
    position_lat: Optional[float] = None
    position_lon: Optional[float] = None
    position_source: Optional[str] = None
    position_status: Optional[str] = None
    position_timestamp: Optional[float] = None

    @property
    def measurement_timestamp(self) -> float:
        """
        Best available measurement time.

        Falls back to received_at ONLY when the source supplied no timestamp, and callers
        can tell the difference because `timestamp` stays None in that case.
        """
        return self.received_at if self.timestamp is None else self.timestamp

    @property
    def speed_is_pwm_derived(self) -> bool:
        return self.vehicle_id in PWM_DERIVED_SPEED_VEHICLES


@dataclass
class IngestResult:
    """Outcome of one ingestion attempt. Servers inspect this instead of catching exceptions."""

    accepted: bool
    vehicle_id: Optional[str] = None
    sequence: Optional[int] = None
    reason: str = "ACCEPTED"
    fields_applied: tuple = field(default_factory=tuple)

    def __bool__(self) -> bool:
        return self.accepted


# Rejection reasons (stable strings for logs and tests).
REJECT_MALFORMED = "REJECTED_MALFORMED"
REJECT_MISSING_VEHICLE_ID = "REJECTED_MISSING_VEHICLE_ID"
REJECT_UNKNOWN_VEHICLE = "REJECTED_UNKNOWN_VEHICLE"
REJECT_NON_FINITE = "REJECTED_NON_FINITE_VALUE"
REJECT_BAD_TIMESTAMP = "REJECTED_INVALID_TIMESTAMP"
REJECT_BAD_SEQUENCE = "REJECTED_INVALID_SEQUENCE"
REJECT_DUPLICATE = "REJECTED_DUPLICATE"
REJECT_OUT_OF_ORDER = "REJECTED_OUT_OF_ORDER"
REJECT_UNSUPPORTED_TRANSPORT = "REJECTED_UNSUPPORTED_TRANSPORT"
REJECT_BAD_SPEED = "REJECTED_INVALID_SPEED"
REJECT_NEGATIVE_SPEED = "REJECTED_NEGATIVE_SPEED"


# =====================================================================
# INGESTOR
# =====================================================================

class TelemetryIngestor:
    """
    The one place telemetry becomes canonical Twin state.

    Concurrency: this object keeps only per-vehicle sequence bookkeeping. The Twin write
    itself is a single atomic `update_vehicle_fields` call, so a packet either lands whole
    or not at all (TwinStateStore holds the lock).
    """

    # A source timestamp further ahead than this is not believable.
    MAX_CLOCK_SKEW_S = 1.0

    def __init__(
        self,
        store,
        unit_converter: Optional[UnitConverter] = None,
        id_mapper: Optional[VehicleIDMapper] = None,
        clock=time.time,
        auto_register: bool = True,
    ):
        self.store = store
        self.clock = clock
        self.auto_register = auto_register
        self.id_mapper = id_mapper if id_mapper is not None else VehicleIDMapper()
        # UnitConverter reads config/physical_vehicle_parameters.json for MEASURED wheel
        # radii. Without it, encoder-derived speed is simply unavailable - never guessed.
        self.unit_converter = unit_converter if unit_converter is not None else UnitConverter()
        self.odometry_calculators: Dict[str, WheelImuOdometryCalculator] = {
            "TRUCK_01": WheelImuOdometryCalculator("TRUCK_01")
        }

        self._last_sequence: Dict[str, int] = {}
        self._seen_sequences: Dict[str, BoundedSequenceTracker] = {}  # D006: bounded
        self.stats: Dict[str, int] = {
            "accepted": 0, "duplicate": 0, "out_of_order": 0,
            "invalid": 0, "unknown_vehicle": 0,
        }

    # -- transport entry points (all converge on ingest_normalized) ----

    def ingest_v2v_packet(self, raw_packet: str, parser=None, is_simulated: bool = False) -> IngestResult:
        """Ingest a frozen-format V2V packet using the EXISTING V2VPacketParser."""
        from v2v_packet_parser import V2VPacketParser

        if parser is None:
            parser = getattr(self, "_v2v_parser", None) or V2VPacketParser()
            self._v2v_parser = parser
        try:
            parsed = parser.parse_v2v_packet(raw_packet)
        except Exception as exc:                    # a parser bug must not kill the server
            logger.warning("v2v parse raised: %s", exc)
            return self._reject(None, None, REJECT_MALFORMED)
        if not parsed:
            return self._reject(None, None, REJECT_MALFORMED)
        return self.ingest_parsed_record(parsed, transport=Transport.V2V, is_simulated=is_simulated)

    def ingest_gateway_record(self, parsed: Dict[str, Any]) -> IngestResult:
        """
        Ingest a record from the LoRa serial gateway.

        The gateway tags each record with `provenance_source`. A record produced by the
        gateway's simulated fallback loop carries SIMULATION and is ingested as such - it
        never masquerades as live hardware.
        """
        if not isinstance(parsed, dict):
            return self._reject(None, None, REJECT_MALFORMED)
        declared = str(parsed.get("provenance_source", "")).upper()
        simulated = declared != "HARDWARE"
        if not declared:
            logger.warning(
                "gateway record carries no provenance_source; ingesting as SIMULATION "
                "(refusing to assume hardware)"
            )
        return self.ingest_parsed_record(parsed, transport=Transport.SERIAL_GATEWAY, is_simulated=simulated)

    def ingest_http_payload(self, payload: Dict[str, Any], is_simulated: bool = False) -> IngestResult:
        """Ingest the JSON body posted to /api/hardware/telemetry."""
        if not isinstance(payload, dict):
            return self._reject(None, None, REJECT_MALFORMED)

        source = str(payload.get("source", "")).upper()
        transport = Transport.DIRECT_WIFI if source == "DIRECT_WIFI" else Transport.V2V
        return self.ingest_parsed_record(payload, transport=transport, is_simulated=is_simulated)

    # -- normalization -------------------------------------------------

    def ingest_parsed_record(self, parsed: Dict[str, Any], transport: str,
                             is_simulated: bool = False) -> IngestResult:
        """Normalize one already-parsed record, then ingest it."""
        if transport not in Transport.ALL:
            return self._reject(parsed.get("vehicle_id") if isinstance(parsed, dict) else None,
                                None, REJECT_UNSUPPORTED_TRANSPORT)
        if not isinstance(parsed, dict):
            return self._reject(None, None, REJECT_MALFORMED)

        vid = parsed.get("vehicle_id")
        if not vid or not isinstance(vid, str) or not vid.strip():
            return self._reject(None, None, REJECT_MISSING_VEHICLE_ID)
        vid = vid.strip().upper()

        seq_raw = parsed.get("sequence_number", parsed.get("sequence"))
        try:
            sequence = int(seq_raw)
        except (TypeError, ValueError):
            return self._reject(vid, None, REJECT_BAD_SEQUENCE)

        received_at = float(self.clock())

        # MEASUREMENT TIMESTAMP - deliberately strict.
        #
        # The frozen V2V wire format carries NO time field:
        #     STATE,TRUCK_0x,seq,rpm,speed,ax,ay,az,gx,gy,gz
        # and neither does the gateway key-value line. The existing parsers stamp
        # `timestamp = time.time()` at PARSE time, which is an arrival time, not a
        # measurement time. Promoting that to a measurement timestamp would misrepresent
        # when the physical quantity was actually sampled.
        #
        # So a measurement time is taken ONLY from a key that explicitly means one
        # (`source_timestamp` / `measurement_timestamp`). A bare `timestamp` from a parser
        # is treated as arrival metadata and left out, so `NormalizedTelemetry.timestamp`
        # stays None and consumers can see that no source time was supplied.
        ts_raw = parsed.get("source_timestamp", parsed.get("measurement_timestamp"))
        timestamp = None
        if ts_raw is not None:
            try:
                timestamp = float(ts_raw)
            except (TypeError, ValueError):
                return self._reject(vid, sequence, REJECT_BAD_TIMESTAMP)

        # D008: type-check nested structures before .get() calls.
        # A non-dict value (string, list, int) would be truthy and survive `or {}`,
        # then crash on `.get("x")` with AttributeError.
        _accel = parsed.get("acceleration")
        accel = _accel if isinstance(_accel, dict) else {}
        _gyro = parsed.get("gyroscope")
        gyro = _gyro if isinstance(_gyro, dict) else {}
        _comm = parsed.get("communication")
        comm = _comm if isinstance(_comm, dict) else {}

        # GAP 1 & GAP 2: speed type and value validation
        # Check if speed was explicitly provided in the payload
        speed_raw = None
        speed_present = False
        for k in ("speed_mps", "speed_value", "speed"):
            if k in parsed:
                speed_present = True
                speed_raw = parsed[k]
                break

        speed_mps_reported = None
        if speed_present and speed_raw is not None:
            if isinstance(speed_raw, bool) or not isinstance(speed_raw, (int, float)):
                return self._reject(vid, sequence, REJECT_BAD_SPEED)
            if not math.isfinite(speed_raw):
                return self._reject(vid, sequence, REJECT_NON_FINITE)
            if speed_raw < 0.0:
                return self._reject(vid, sequence, REJECT_NEGATIVE_SPEED)
            speed_mps_reported = float(speed_raw)

        # First-class GNSS position extraction (Rules 1-12)
        _pos = parsed.get("position")
        pos_dict = _pos if isinstance(_pos, dict) else {}
        pos_lat = _opt_float(parsed.get("latitude", parsed.get("lat", pos_dict.get("latitude", pos_dict.get("lat")))))
        pos_lon = _opt_float(parsed.get("longitude", parsed.get("lon", pos_dict.get("longitude", pos_dict.get("lon")))))
        pos_source = parsed.get("position_source", pos_dict.get("source"))
        pos_status = parsed.get("position_status", pos_dict.get("status"))
        pos_ts = _opt_float(parsed.get("position_timestamp", pos_dict.get("timestamp")))

        pulse_cnt = _opt_int(parsed.get("pulse_count", parsed.get("pulses", parsed.get("encoder_pulses"))))
        delta_pulses = _opt_int(parsed.get("delta_pulses", parsed.get("pulses_delta")))

        normalized = NormalizedTelemetry(
            vehicle_id=vid,
            sequence=sequence,
            received_at=received_at,
            timestamp=timestamp,
            transport=transport,
            is_simulated=is_simulated,
            rpm=_opt_float(parsed.get("rpm")),
            speed_mps_reported=speed_mps_reported,
            ax_mps2=_opt_float(accel.get("x")),
            ay_mps2=_opt_float(accel.get("y")),
            az_mps2=_opt_float(accel.get("z")),
            gx_rad_s=_opt_float(gyro.get("x")),
            gy_rad_s=_opt_float(gyro.get("y")),
            gz_rad_s=_opt_float(gyro.get("z")),
            pulse_count=pulse_cnt,
            delta_pulses=delta_pulses,
            communication_state=parsed.get("communication_state") or parsed.get("communication_status"),
            raw_quality=parsed.get("data_quality"),
            rssi=_opt_float(comm.get("rssi", parsed.get("rssi"))),
            snr=_opt_float(comm.get("snr", parsed.get("snr"))),
            position_lat=pos_lat,
            position_lon=pos_lon,
            position_source=str(pos_source) if pos_source is not None else None,
            position_status=str(pos_status) if pos_status is not None else None,
            position_timestamp=pos_ts,
        )
        return self.ingest_normalized(normalized)

    # -- the boundary ---------------------------------------------------

    def ingest_normalized(self, t: NormalizedTelemetry) -> IngestResult:
        """
        Validate, order-check and apply one normalized observation.

        Nothing touches the Twin until every check below has passed.
        """
        # 1. known vehicle
        if not self.id_mapper.is_mapped_physical(t.vehicle_id):
            self.stats["unknown_vehicle"] += 1
            logger.warning("telemetry rejected: unknown vehicle %s seq=%s", t.vehicle_id, t.sequence)
            return self._reject(t.vehicle_id, t.sequence, REJECT_UNKNOWN_VEHICLE)

        # 2. sequence sanity
        if t.sequence < 0:
            return self._reject(t.vehicle_id, t.sequence, REJECT_BAD_SEQUENCE)

        # 3. timestamp sanity (NaN, Inf, negative, implausibly far in the future)
        if t.timestamp is not None:
            if not math.isfinite(t.timestamp) or t.timestamp < 0:
                return self._reject(t.vehicle_id, t.sequence, REJECT_BAD_TIMESTAMP)
            if t.timestamp > t.received_at + self.MAX_CLOCK_SKEW_S:
                return self._reject(t.vehicle_id, t.sequence, REJECT_BAD_TIMESTAMP)

        # 4. numeric sanity - NaN / Inf anywhere means the packet is not trustworthy
        for name in ("rpm", "speed_mps_reported", "ax_mps2", "ay_mps2", "az_mps2",
                     "gx_rad_s", "gy_rad_s", "gz_rad_s"):
            value = getattr(t, name)
            if value is not None and not math.isfinite(value):
                logger.warning("telemetry rejected: non-finite %s for %s seq=%s",
                               name, t.vehicle_id, t.sequence)
                return self._reject(t.vehicle_id, t.sequence, REJECT_NON_FINITE)

        # GAP 2: Negative speed rejection
        if t.speed_mps_reported is not None and t.speed_mps_reported < 0.0:
            logger.warning("telemetry rejected: negative speed %s for %s seq=%s",
                           t.speed_mps_reported, t.vehicle_id, t.sequence)
            return self._reject(t.vehicle_id, t.sequence, REJECT_NEGATIVE_SPEED)

        # 5. duplicate / out-of-order — BEFORE any Twin mutation
        # D006: ordering is decided by last_accepted_sequence. The bounded tracker
        # is only used for duplicate detection within the recent window.
        last_seq = self._last_sequence.get(t.vehicle_id)
        if last_seq is not None and t.sequence < last_seq:
            self.stats["out_of_order"] += 1
            logger.info("telemetry out-of-order ignored: %s seq=%s (last=%s)",
                        t.vehicle_id, t.sequence, last_seq)
            return self._reject(t.vehicle_id, t.sequence, REJECT_OUT_OF_ORDER)

        seen = self._seen_sequences.setdefault(t.vehicle_id, BoundedSequenceTracker())
        if t.sequence in seen:
            self.stats["duplicate"] += 1
            logger.info("telemetry duplicate ignored: %s seq=%s", t.vehicle_id, t.sequence)
            return self._reject(t.vehicle_id, t.sequence, REJECT_DUPLICATE)

        # 6. build the field set (provenance decided here, never by the store)
        fields = self._build_twin_fields(t)

        # 7. apply atomically
        if self.store.get_vehicle(t.vehicle_id) is None:
            if not self.auto_register:
                return self._reject(t.vehicle_id, t.sequence, REJECT_UNKNOWN_VEHICLE)
            # A physical truck may exist in the Twin with no simulation Vehicle object.
            self.store.register_vehicle(t.vehicle_id)

        self.store.update_vehicle_fields(t.vehicle_id, fields)

        seen.add(t.sequence)
        self._last_sequence[t.vehicle_id] = max(last_seq or 0, t.sequence)
        self.stats["accepted"] += 1

        logger.info(
            "telemetry accepted: vehicle=%s seq=%s transport=%s source=%s ts=%s received_at=%.3f fields=%d",
            t.vehicle_id, t.sequence, t.transport,
            "SIMULATION" if t.is_simulated else "HARDWARE",
            t.timestamp, t.received_at, len(fields),
        )
        return IngestResult(True, t.vehicle_id, t.sequence, "ACCEPTED", tuple(sorted(fields)))

    # -- provenance ------------------------------------------------------

    def _build_twin_fields(self, t: NormalizedTelemetry) -> Dict[str, Any]:
        """
        Decide the provenance of every reported field.

        A field the packet did not carry is simply absent from the returned dict, so the
        Twin keeps it UNAVAILABLE instead of storing a fabricated value.
        """
        from twin.twin_state_store import ClockDomain, Quality, Source, Sourced

        observed = Source.SIMULATION if t.is_simulated else Source.HARDWARE
        derived = Source.SIMULATION if t.is_simulated else Source.DERIVED
        quality = map_quality(t.raw_quality)
        if quality is Quality.UNKNOWN:
            quality = Quality.GOOD          # it passed validation and arrived intact
        ts = t.measurement_timestamp

        # P4: `origin` records what ULTIMATELY stands behind the value. For a real packet
        # that is the hardware, even when the stored `source` is DERIVED because a
        # calculation sat in between. Field-level precedence uses this so a simulated
        # value cannot quietly displace something a sensor produced.
        origin = None if t.is_simulated else Source.HARDWARE

        # P4.1: telemetry timestamps - both a device measurement time and our own
        # received_at - are wall-clock epoch seconds. Emulated packets ingested through
        # this path are also stamped by a wall clock, so the domain is WALL_CLOCK
        # regardless of provenance. The domain describes the CLOCK, not the source.
        domain = ClockDomain.WALL_CLOCK

        fields: Dict[str, Any] = {}

        def put(name, value, source, q=quality):
            if value is None:
                return                      # not reported => stays UNAVAILABLE
            assert name not in NEVER_FROM_HARDWARE, f"{name} is not measurable on this prototype"
            fields[name] = Sourced(value=value, timestamp=ts, source=source, quality=q,
                                   origin=origin, clock_domain=domain)

        # Encoder RPM is a genuine measurement.
        put("rpm", t.rpm, observed)

        # IMU is genuine hardware data.
        put("ax_mps2", t.ax_mps2, observed)
        put("ay_mps2", t.ay_mps2, observed)
        put("az_mps2", t.az_mps2, observed)
        put("gx_rad_s", t.gx_rad_s, observed)
        put("gy_rad_s", t.gy_rad_s, observed)
        put("gz_rad_s", t.gz_rad_s, observed)

        # Speed. Two very different things share one wire field, so they are stored apart.
        if t.speed_is_pwm_derived:
            # PWM-derived: NOT an encoder measurement. Kept under its own name so no
            # consumer can mistake it for one, and `speed_mps` stays unavailable unless a
            # measured RPM lets us derive it below.
            put("speed_mps_pwm_derived", t.speed_mps_reported, derived)
        else:
            put("speed_mps_reported", t.speed_mps_reported, derived)

        # Encoder-derived speed, computed by the EXISTING UnitConverter from the MEASURED
        # wheel radius in config/physical_vehicle_parameters.json. Unavailable (not zero,
        # not guessed) when the vehicle has no calibrated radius.
        if t.rpm is not None:
            speed_from_rpm = self.unit_converter.rpm_to_speed_mps(t.vehicle_id, t.rpm)
            if speed_from_rpm is not None:
                put("speed_mps", speed_from_rpm, derived)

        # Link health is observed from packet arrival, not measured by a sensor.
        put("communication_state", t.communication_state, derived)

        # ------------------------------------------------------------------
        # RADIO METRICS ARE PER-RADIO. A Wi-Fi number is not a LoRa number.
        #
        # Both radios used to write into one shared `rssi_dbm` / `snr_db` pair, so a
        # Wi-Fi RSSI and a LoRa RSSI were indistinguishable downstream and the HMI
        # could show a Wi-Fi reading under a V2V heading. The metric now follows the
        # TRANSPORT the frame actually arrived on:
        #
        #   DIRECT_WIFI           -> wifi_rssi_dbm. No LoRa radio was involved, so
        #                            lora_rssi_dbm and lora_snr_db stay UNAVAILABLE.
        #   V2V / SERIAL_GATEWAY  -> lora_rssi_dbm + lora_snr_db, measured by the
        #                            receiving LoRa modem (packetRssi / packetSnr).
        #   EMULATOR              -> neither. An emulated frame crossed no radio.
        #
        # A value is never copied between radios, and an absent metric is left absent
        # rather than filled in from the other radio.
        # ------------------------------------------------------------------
        if t.transport == Transport.DIRECT_WIFI:
            put("wifi_rssi_dbm", t.rssi, observed)
        elif t.transport in (Transport.V2V, Transport.SERIAL_GATEWAY):
            put("lora_rssi_dbm", t.rssi, observed)
            put("lora_snr_db", t.snr, observed)

        # LEGACY, retained so existing consumers keep working. Ambiguous by
        # construction - it does not say which radio produced it. New code must read
        # the per-radio fields above.
        put("rssi_dbm", t.rssi, observed)
        put("snr_db", t.snr, observed)

        # First-class GNSS position handling (Rules 1-12)
        if t.position_lat is not None and t.position_lon is not None:
            is_valid_lat = math.isfinite(t.position_lat) and -90.0 <= t.position_lat <= 90.0
            is_valid_lon = math.isfinite(t.position_lon) and -180.0 <= t.position_lon <= 180.0
            pos_src_ok = (t.position_source or "GNSS").upper() in ("GNSS", "GPS")
            pos_stat_ok = (t.position_status or "VALID").upper() in ("VALID", "OK", "FIX")

            if is_valid_lat and is_valid_lon and pos_src_ok and pos_stat_ok:
                # POSITIVE EVIDENCE, NOT ABSENCE OF DENIAL.
                #
                # A fix is physical only when the vehicle is on the documented
                # receiver allowlist. `is_simulated` alone is not enough: it defaults
                # to False whenever a caller omits it, so trusting it made silence
                # equivalent to a hardware claim.
                physical_fix = (
                    not t.is_simulated
                    and origin == Source.HARDWARE
                    and t.vehicle_id in GNSS_EQUIPPED_VEHICLES
                )
                pos_origin = "HARDWARE" if physical_fix else "SOFTWARE_ONLY"

                # The guard covers this field too. A HARDWARE stamp without a verified
                # receiver is a programming error, not a data condition.
                assert not (
                    pos_origin == "HARDWARE" and t.vehicle_id not in GNSS_EQUIPPED_VEHICLES
                ), "position_gnss stamped HARDWARE for a vehicle with no verified receiver"
                gnss_payload = {
                    "latitude": float(t.position_lat),
                    "longitude": float(t.position_lon),
                    "source": "GNSS",
                    "status": "VALID",
                    "timestamp": t.position_timestamp if t.position_timestamp is not None else ts,
                    "received_at": t.received_at,
                    "origin": pos_origin,
                    "transport": t.transport,
                }
                fields["position_gnss"] = Sourced(
                    value=gnss_payload,
                    timestamp=t.position_timestamp if t.position_timestamp is not None else ts,
                    # The wrapper is what every consumer reads for provenance, so it
                    # must say the same thing as the payload above. Stamping the
                    # wrapper HARDWARE while the payload said SOFTWARE_ONLY is how a
                    # synthetic coordinate reached the frontend as a physical fix.
                    source=observed if physical_fix else Source.SIMULATION,
                    quality=quality,
                    origin=origin if physical_fix else None,
                    clock_domain=domain,
                )
            else:
                logger.warning(
                    "GNSS position rejected (Rule 9 invalid coordinate/status/source): vehicle=%s lat=%s lon=%s status=%s source=%s",
                    t.vehicle_id, t.position_lat, t.position_lon, t.position_status, t.position_source,
                )

        # Pass 2: Physical local odometry calculation
        if t.vehicle_id == "TRUCK_01":
            calc = self.odometry_calculators.get("TRUCK_01")
            if calc is not None:
                odom_payload = calc.update(
                    timestamp=ts,
                    pulse_count=t.pulse_count,
                    delta_pulses=t.delta_pulses,
                    gz_rad_s=t.gz_rad_s,
                    is_simulated=t.is_simulated,
                )
                fields["position_odom"] = Sourced(
                    value=odom_payload,
                    timestamp=ts,
                    source=Source.DERIVED,
                    origin=Source.SIMULATION if t.is_simulated else Source.HARDWARE,
                    quality=Quality.GOOD if odom_payload.get("status") == "VALID" else Quality.STALE,
                    clock_domain=domain,
                )
        elif t.vehicle_id == "TRUCK_02":
            fields["position_odom"] = Sourced(
                value={
                    "x_m": None,
                    "y_m": None,
                    "heading_rad": None,
                    "distance_m": None,
                    "timestamp": ts,
                    "source": "UNKNOWN",
                    "origin": "UNKNOWN",
                    "provenance_label": "UNAVAILABLE",
                    "method": "NONE",
                    "status": "UNAVAILABLE",
                    "origin_type": "NONE",
                    "reason": "TRUCK_02 odometry is not supported in Pass 2",
                    "verification_label": "CONTRACT VERIFIED",
                },
                timestamp=ts,
                source=Source.UNKNOWN,
                origin=Source.UNKNOWN,
                quality=Quality.UNKNOWN,
                clock_domain=domain,
            )

        # Bookkeeping that must never be confused with a measurement time.
        fields["received_at"] = Sourced(
            value=t.received_at, timestamp=t.received_at, source=Source.DERIVED,
            quality=Quality.GOOD, clock_domain=domain
        )
        fields["sequence"] = Sourced(
            value=t.sequence, timestamp=ts, source=observed, quality=Quality.GOOD,
            origin=origin, clock_domain=domain
        )
        fields["telemetry_transport"] = Sourced(
            value=t.transport, timestamp=ts, source=Source.DERIVED, quality=Quality.GOOD,
            clock_domain=domain
        )
        return fields

    # -- helpers ---------------------------------------------------------

    def _reject(self, vehicle_id, sequence, reason) -> IngestResult:
        if reason not in (REJECT_DUPLICATE, REJECT_OUT_OF_ORDER, REJECT_UNKNOWN_VEHICLE):
            self.stats["invalid"] += 1
        return IngestResult(False, vehicle_id, sequence, reason)


def _opt_float(value: Any) -> Optional[float]:
    """Best-effort float. Returns None for absent/unparseable values - never a zero stand-in."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _opt_int(value: Any) -> Optional[int]:
    """Best-effort int. Returns None for absent/unparseable values."""
    if value is None or isinstance(value, bool):
        return None
    try:
        val = int(value)
        return val if math.isfinite(val) else None
    except (TypeError, ValueError):
        return None
