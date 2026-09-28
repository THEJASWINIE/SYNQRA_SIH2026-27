# FOG-ORCHESTRATOR 2.0 — Comprehensive System Overview
**SIH 2026-27 | Problem Statement: SIH26007**
**Ministry of Steel / NMDC Limited (Bailadila Iron Ore Complex)**

---

## 1. Operational Problem & Industry Gap

Open-cast iron ore mining at NMDC Bailadila (Deposit 5) takes place in mountainous terrain subject to severe monsoon cloud-inversion and winter valley fog. When visibility drops below 15 meters:
- **Optical Sensors Fail**: Standard cameras, LiDAR (fog backscatter), and human vision become ineffective.
- **Extreme Braking Physics**: A 165.5-tonne loaded BEML BH100 dumper travelling at 35 km/h on an 8% to 12% wet haul road requires 35 to 50 meters to stop.
- **The Operational Dilemma**: Mines currently face a binary choice—continue hauling blindly (severe collision hazard) or institute complete fleet stoppage (millions of INR lost per hour).

---

## 2. The FOG-ORCHESTRATOR Solution

FOG-ORCHESTRATOR 2.0 replaces blind haulage and blanket shutdowns with **Continuous Physics-Constrained Speed Guidance**:
1. **Weather Ingestion**: Haul road weather stations continuously measure optical visibility ($V_{vis}$) and wet surface friction priors ($\mu$).
2. **Authoritative 3D Digital Twin**: Single authoritative model mirrors real spatial topography, road grades, and vehicle dynamic states.
3. **5-Constraint Physics Governor**: Solves the maximum safe speed $v_{safe} = \min(v_{stop}, v_{retarder}, v_{traction}, v_{curve}, v_{mine})$.
4. **Driver-Assistance In-Cab Guidance**: Cockpit screen provides live speedometer, safe speed ceiling, and audible cautions. **The human driver remains in authoritative physical control.**
5. **Dual-Link RF Telemetry**: 433 MHz LoRa and 2.4 GHz Wi-Fi dual-link telemetry with automatic Safe Beacon failover.

---

## 3. Key System Differentiators

| Feature | Conventional Mining Practice | FOG-ORCHESTRATOR 2.0 |
| :--- | :--- | :--- |
| **Low-Visibility Operation** | Blanket fleet shutdown ($0\text{ t/h}$) or high-risk blind driving | Regulated safe crawl pacing retaining **68.4% nominal throughput** |
| **Safety Enforcement** | Driver visual estimation | Inviolable physics-based speed ceiling ($v_{safe}$) calculated in real time |
| **Vehicle Control Authority** | Human or autonomous control confusion | **Driver remains in full control**; system provides advisory guidance & warnings |
| **Digital Twin Role** | Static visual dashboard | **Authoritative cyber-physical state store** with live & predictive modes |
| **Communication Resilience**| Single cellular/Wi-Fi point of failure | **Dual-link LoRa (433 MHz) + Wi-Fi + SAE J1939 CAN** with 1 Hz Safe Beacon |

---

## 4. Hardware and Software Integration Summary

- **Physical Bench Prototype**: Dual ESP32-WROOM-32 microcontrollers with slotted optical wheel encoders, MPU6050 6-DOF IMU, L298N (Truck 01) and TB6612FNG (Truck 02) motor drivers, SX1278 LoRa transceivers, and TWAI CAN controllers.
- **Backend Architecture**: FastAPI asynchronous server (`/api/hardware/telemetry`, `/api/environment/fog`), single authoritative `twin_state_store.py`, and sub-15ms WebSocket state broadcast.
- **Frontend Suites**: Control Room 3D Corridor Console (React 19 / Three.js on Port 5173), Driver Cockpit Screens (`truck01.html`, `truck02.html` on Ports 3001/3002), and MineCast Weather Console.
