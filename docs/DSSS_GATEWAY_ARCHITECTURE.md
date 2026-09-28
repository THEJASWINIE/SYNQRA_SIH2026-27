# DSSS / PN GATEWAY COMMUNICATION ARCHITECTURE
## FOG-ORCHESTRATOR 2.0 — SIH 2026-27
**Target Mine Reference:** NMDC Bailadila Deposit 5, Bacheli Complex, Chhattisgarh  
**Status:** CANONICAL ARCHITECTURAL & RESEARCH MODEL SPECIFICATION  
**Module Reference:** `integration_adapters/dsss_gateway_selector.py`  
**Configuration Reference:** `config/gateway_network_config.json`  
**Date:** 2026-09-18  

---

## 1. MANDATORY ZERO FABRICATION DISCLAIMER (PART 12)

> [!IMPORTANT]
> **Separation of Physical Hardware Prototype from Research DSSS Model**:
> - **Physical Hardware Status:** The current physical bench prototype utilizes **Semtech SX1278 (AI-Thinker Ra-02) transceivers operating on Chirp Spread Spectrum (CSS) LoRa at $433\text{ MHz}$**.
> - **DSSS Model Status:** The Direct-Sequence Spread-Spectrum (DSSS) pseudo-noise (PN) sequence correlation model, multi-gateway signature beaconing, and anti-flapping handover engine described in this document are **ARCHITECTURAL RESEARCH & SIMULATION MODELS**.
> - **Zero Fabrication Commitment:** No claim is made that the existing SX1278 hardware is executing direct PN chipping sequences or CDMA-style physical despreading. Physical multi-gateway DSSS hardware requires dedicated baseband ASIC/FPGA transceivers planned for post-SIH field development.

---

## 2. END-TO-END COMMUNICATION TOPOLOGY

```
 TRUCK_01 (ESP32)                              TRUCK_02 (ESP32)
 ┌─────────────────────────┐                   ┌─────────────────────────┐
 │ Local Vehicle State     │                   │ Local Vehicle State     │
 │ Local Safety Governor   │                   │ Local Safety Governor   │
 │ CSS-LoRa 433MHz PHY     │◄───Direct V2V────►│ CSS-LoRa 433MHz PHY     │
 └───────────┬─────────────┘                   └───────────┬─────────────┘
             │                                             │
             └──────────────────────┬──────────────────────┘
                                    │ RF Telemetry / Beacons
                                    ▼
                    ┌───────────────────────────────┐
                    │     DSSS / PN GATEWAY LAYER   │
                    │   (4 Site-Distributed Nodes)  │
                    └───────────────┬───────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
   GW-01 (PN-A)               GW-02 (PN-B)               GW-03 (PN-C)
   Pit Rim Mast               Crusher Overlook           Ramp Switchback 3
   Elev: 1245m                Elev: 1280m                Elev: 1210m
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    │
                                    ▼ High-Speed Optical / Wi-Fi Backhaul
                           ┌─────────────────┐
                           │   MINE NETWORK  │
                           └────────┬────────┘
                                    ▼
                           ┌─────────────────┐
                           │ FastAPI Backend │
                           └────────┬────────┘
                                    ▼
                           ┌─────────────────┐
                           │  TwinStateStore │
                           └────────┬────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │ FOG-ORCHESTRATOR INTELLIGENCE │
                    │ (Dispatch, Safe Speed, Slots) │
                    └───────────────────────────────┘
```

---

## 3. PSEUDO-NOISE (PN) GATEWAY IDENTITY & BEACONING (PART 13)

To overcome heavy multi-path reflections and severe shadowing caused by steep open-cast benches in Bailadila Deposit 5, each gateway transmits a continuous, known pseudo-noise code signature.

### 3.1 Gateway Identities & Code Assignment
Per `config/gateway_network_config.json`:
- **GW-01 $\to$ PN-A:** Pit Rim North Mast ($1{,}245\text{ m}$ elevation, $433.175\text{ MHz}$)
- **GW-02 $\to$ PN-B:** Primary Crusher Hopper Overlook ($1{,}280\text{ m}$ elevation, $433.375\text{ MHz}$)
- **GW-03 $\to$ PN-C:** Haul Ramp Switchback 3 Relay Tower ($1{,}210\text{ m}$ elevation, $433.575\text{ MHz}$)
- **GW-04 $\to$ PN-D:** South Pit Bottom Shovel Loading Sector ($1{,}175\text{ m}$ elevation, $433.775\text{ MHz}$)

### 3.2 Vehicle PN Correlation Sequence
The vehicle receiver continuously correlates incoming RF signals against known gateway PN sequences:
$$\rho_{i}(\tau) = \frac{1}{L} \sum_{k=0}^{L-1} r(k + \tau) \cdot \text{PN}_i(k)$$
where $L = 127$ (Gold code chip length), and $\rho_i \in [0.0, 1.0]$ represents the normalized correlation score.

**Decision Chain:**
$$\text{RF Signal} \to \text{Synchronization} \to \text{PN Correlation} \to \text{Correlation Score } (\rho_i) \to \text{Signal/Link Quality} \to \text{Candidate Selection} \to \text{Handover Decision}$$

> [!NOTE]
> Geographic proximity (GNSS distance) is **NOT** the gateway selection metric. In complex pit terrain, line-of-sight and RF diffraction determine link viability; correlation score $\rho_i$ and RSSI/SNR are the primary metrics.

---

## 4. GATEWAY SELECTION STATE MACHINE & HYSTERESIS (PART 14)

To prevent gateway flapping at pit rim boundaries and switchbacks, the selection state machine enforces strict hysteresis and persistence.

```
       ┌────────────────────────┐
       │       NO_GATEWAY       │◄────────────────────────┐
       └───────────┬────────────┘                         │
                   │                                      │ Timeout expired
                   │ Best rho >= MIN_CORR                 │ or RF loss
                   ▼                                      │
       ┌────────────────────────┐                         │
       │       CONNECTED        │─────────────────────────┤
       └───────────┬────────────┘                         │
                   │ Candidate rho > Current + SWITCH_MGN │
                   ▼                                      │
       ┌────────────────────────┐                         │
       │    HANDOVER_PENDING    │─────────────────────────┘
       └───────────┬────────────┘
                   │ N >= PERSISTENCE_COUNT
                   ▼
       ┌────────────────────────┐
       │     HANDOVER (EXEC)    │
       └────────────────────────┘
```

### 4.1 Selection Parameters
- `SWITCH_MARGIN`: $0.15$ (normalized correlation differential). Candidate must exceed current gateway by at least $15\%$ correlation.
- `MIN_CORRELATION`: $0.40$. Below $0.40$, packets cannot be reliably decoded.
- `DEGRADED_CORRELATION`: $0.60$. Below $0.60$, link enters `DEGRADED` state.
- `PERSISTENCE_COUNT`: $3$ consecutive observations. Candidate advantage must be sustained for 3 beacon cycles.
- `FAIL_TIMEOUT`: $1.50\text{ s}$. If current gateway beacon is missing for $>1.5\text{ s}$, immediate failover or transition to `NO_GATEWAY` is triggered.
- `MIN_SIGNAL_RSSI`: $-115.0\text{ dBm}$. Physical receiver sensitivity floor.

---

## 5. DSSS LINK STATES & TELEMETRY CONTRACT (PART 15)

Every vehicle transmits its communication link state in its telemetry payload:
- **`CONNECTED`**: Reliable packet flow ($\rho \ge 0.60$, packet loss $< 25\%$).
- **`DEGRADED`**: Marginal packet flow ($0.40 \le \rho < 0.60$ or packet loss $\ge 25\%$).
- **`HANDOVER`**: Actively executing gateway transition.
- **`DISCONNECTED`**: No gateway satisfies minimum thresholds; fail-safe governor assumes total local authority.

### Telemetry Output Schema
```json
{
  "gateway_id": "GW-02",
  "correlation_score": 0.8850,
  "rssi_dbm": -68.40,
  "snr_db": 8.20,
  "packet_sequence": 1420,
  "packet_loss_rate": 0.0500,
  "last_valid_packet_timestamp": 1726650420.150,
  "link_state": "CONNECTED",
  "selection_state": "CONNECTED",
  "candidate_gateway_id": null,
  "persistence_progress": 0
}
```

---

## 6. AUTOMATED TEST VERIFICATION

The DSSS gateway selection architecture is verified by `tests/test_dsss_gateway_selection.py`:
- Cold start selection: selects highest correlation gateway above $0.40$.
- Weak signal rejection: rejects signals with $\rho < 0.40$ or $\text{RSSI} < -115\text{ dBm}$.
- Handover margin: rejects candidate improving by only $0.07$ ($< 0.15$).
- Persistence count: candidate with $\Delta\rho = 0.23$ must persist for exactly 3 cycles before handover executes.
- Anti-flapping: transient noise spikes ($1$ cycle) do not trigger handover.
- Timeout failover: loss of primary gateway for $>1.5\text{ s}$ triggers immediate failover to viable alternative.
