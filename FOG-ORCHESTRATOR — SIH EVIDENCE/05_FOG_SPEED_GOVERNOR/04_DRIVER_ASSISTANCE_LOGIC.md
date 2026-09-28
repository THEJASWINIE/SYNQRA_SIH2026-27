# FOG-ORCHESTRATOR 2.0 — In-Cab Driver Assistance & Human Authority
**Document ID:** `DOC-05-FSG-04` | **Audited Standard:** Human-in-the-Loop Functional Safety

---

## 1. Critical Operational Principle: Human Remains in Control

A foundational premise of FOG-ORCHESTRATOR 2.0 is that **the system does NOT autonomously apply emergency braking or steer the vehicle**:
- **Why Autonomous Stopping is Rejected in Heavy Mines**: An unexpected autonomous full brake application on a 165.5-tonne haul dumper travelling downhill on an 8% wet ramp can induce catastrophic hydraulic wheel lockup, jackknifing, or rollover.
- **The Correct Architecture**: **Driver-Assistance Safety Governor & In-Cab Advisory Guidance**.
- **Role of the System**: Continuously advises the driver of the exact safe speed ceiling, monitors operator compliance, and emits progressive audio-visual alerts when deceleration is required.

---

## 2. In-Cab Cockpit Console Warning States

The high-contrast driver displays (`truck01.html`, `truck02.html`) present four distinct states:

| Warning State | Visual Indicator | Audible Chime | Operational Instruction to Driver |
| :--- | :--- | :--- | :--- |
| **NORMAL** | Solid Green Speed Ring | None | Speed is within safe physics envelope. Maintain haul cycle. |
| **CAUTION** | Solid Amber Speed Ring | Single Alert Beep | Entering fog zone or approaching grade. Prepare to retard. |
| **SLOW DOWN** | Flashing Red Speed Ring | Continuous Pulse | Actual speed exceeds safe speed. Apply service brake / retarder. |
| **SEVERE STOP** | Solid High-Contrast Red | Urgent Warning Chime | Visibility < 30m. Decelerate to crawl (5 km/h) and pull into passing bay. |
