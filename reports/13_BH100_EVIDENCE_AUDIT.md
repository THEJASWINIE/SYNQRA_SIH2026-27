# 13 — BEML BH100 OEM PARAMETER & EVIDENCE AUDIT
## FOG-ORCHESTRATOR 2.0 — PHASE 7.3.1 AUDIT REPORT

| Document ID | Canonical File Path | Date | Audit Status | Evidence Level |
| :--- | :--- | :--- | :--- | :--- |
| **REP-731-13** | `reports/13_BH100_EVIDENCE_AUDIT.md` | 2026-09-18 | **FROZEN / LOCKED** | OEM_DOCUMENTED (L2) |

---

### 1. BEML BH100 OEM Reference Vehicle Dossier

The reference heavy earth-moving machine (HEMM) used for all vehicle dynamics, kinematic stopping, and fleet simulations is the **BEML BH100**, an Indian-manufactured $100\text{-tonne}$ class rigid rear dump truck widely deployed in open-cast mines operated by NMDC and Coal India Limited.

* **Manufacturer**: BEML Limited (formerly Bharat Earth Movers Limited), Mining & Construction Division, Bangalore, India.
* **Primary Reference Document**: *BEML Dump Trucks — Technical Specification & Equipment Catalog, Document Revision BH100-TS-2018-R2*.
* **Secondary Reference Document**: *BEML Operations & Maintenance Manual for Mining Equipment (Section 4: Hydraulic and Braking Systems)*.

---

### 2. Parameter Forensic Provenance & Discrepancy Reconciliation

```
========================================================================================================================
PARAMETER            CANONICAL VALUE  OEM SOURCE SPECIFICATION            DISCREPANCY / RESOLUTION             STATUS
========================================================================================================================
Gross Vehicle Weight 165,500.0 kg     74,000 kg tare + 91,500 kg payload  Reconciled: Some brochures cite      LOCKED (GREEN)
(GVW)                                                                     rounded 165,000 kg. Exact sum of
                                                                          tare + 91.5t rated payload is 165,500 kg.
Unladen Tare Mass    74,000.0 kg      Chassis, ROPS cab, body & fluids    Verified across all OEM datasheets   LOCKED (GREEN)
Rated Payload        91,500.0 kg      Nominal 100-ton class payload (91.5t) Verified: 91.5 metric tonnes nominal LOCKED (GREEN)
Overall Length       10.52 m          Bumper tip to canopy peak           Verified in dimensional layout draw  LOCKED (GREEN)
Overall Width        5.52 m           Outside tire to outside tire        Verified in dimensional layout draw  LOCKED (GREEN)
Overall Height       5.25 m           Top of ROPS canopy to ground        Verified in dimensional layout draw  LOCKED (GREEN)
Axle Wheelbase       5.25 m           Front steering to rear tandem axle  Verified in dimensional layout draw  LOCKED (GREEN)
Turning Radius       10.80 m          Clearance radius of outer wheel     Verified in steering specification   LOCKED (GREEN)
Tire Size & Type     27.00R49 E-4     Bridgestone radial mining dumper    Loaded rolling radius = 1.35 m       LOCKED (GREEN)
Diesel Engine        Cummins KTA38-C  12-cylinder V-type turbo diesel     Gross power: 770 kW (1,032 HP @ 2100) LOCKED (GREEN)
Automatic Trans      Allison 9680     Planetary power-shift with lockup   6 forward speeds, 1 reverse gear     LOCKED (GREEN)
Front Service Brake  Caliper Disc     Dry single disc per wheel           Pneumatic-over-hydraulic caliper     LOCKED (GREEN)
Rear Service Brake   Wet Multi-Disc   Oil-cooled multi-disc brake pack    Functions as service and retarder    LOCKED (GREEN)
Retarder Absorption  1,200 kW         Continuous hydraulic oil cooling    Thermal dissipation ceiling          LOCKED (GREEN)
Max Mechanical Brake 550,000 N        Full-system clamping force limit    Corresponds to ~3.32 m/s^2 loaded    LOCKED (GREEN)
Wheel Decel Telemetry UNKNOWN         Requires active machine logging     No on-vehicle CAN logger deployed    OPEN (YELLOW)
========================================================================================================================
```

---

### 3. Resolution of Conflicting Sources

#### Discrepancy 1: Gross Operating Machine Weight ($165,000\text{ kg}$ vs $165,500\text{ kg}$)
* **Source A (Marketing Brochure)**: Cites gross machine weight as $165,000\text{ kg}$ ($165\text{ tonnes}$).
* **Source B (Engineering Datasheet)**: Lists empty unladen tare mass as $74,000\text{ kg}$ and nominal rated payload capacity as $91,500\text{ kg}$ ($91.5\text{ tonnes}$).
* **Forensic Resolution**:
  $$\text{True Gross Operating Mass} = 74,000\text{ kg} + 91,500\text{ kg} = \mathbf{165,500\text{ kg}}$$
  The $165,000\text{ kg}$ figure is an informal rounded marketing convenience. The canonical model adopts **$165,500\text{ kg}$** to maintain exact mass conservation when hauling rated $91.5\text{ t}$ iron ore loads.

#### Discrepancy 2: Retarder Absorption Power ($1,200\text{ kW}$ vs $1,050\text{ kW}$)
* **Source A**: Cites continuous retarder power as $1,200\text{ kW}$ under maximum cooling fan and auxiliary pump speed.
* **Source B**: Cites continuous retarder power as $1,050\text{ kW}$ at intermediate engine RPM ($1,600\text{ rpm}$).
* **Forensic Resolution**: The canonical parameter is locked at **$1,200\text{ kW}$** for rated speed ($2,100\text{ rpm}$), with sensitivity checks evaluated down to $900\text{ kW}$.

---

### 4. Remaining Open Validation

* **On-Chassis Hydraulic Pressure Transducer Logging**: Direct physical measurement of hydraulic line pressure rise on an operational BH100 at Bailadila has not been performed by the project team. Laboratory surrogate bench data is used. **Classified as OPEN / YELLOW for real-world field deployment.**
