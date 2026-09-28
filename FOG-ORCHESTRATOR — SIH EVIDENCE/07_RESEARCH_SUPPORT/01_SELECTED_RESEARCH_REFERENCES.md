# FOG-ORCHESTRATOR 2.0 — Foundational Standards & Research References
**Document ID:** `DOC-07-RES-01` | **Audited Standard:** Literature & Standards Grounding

---

## 1. Selected Foundational References Matrix

To guarantee strict compliance with industry standards and safety regulations, FOG-ORCHESTRATOR 2.0 is grounded in seven authoritative references:

| Reference / Standard | Authority / Institution | Relevance to FOG-ORCHESTRATOR 2.0 | Supported Subsystem |
| :--- | :--- | :--- | :--- |
| **1. DGMS Tech Circulars (Haulage Safety)** | Directorate General of Mines Safety, Ministry of Labour (Govt of India) | Mandates maximum 40 km/h haulage, sightline braking clearances, and mandatory speed governors in low visibility. | System Overview & Mine Regulations |
| **2. SAE J1939-71 Vehicle Application Layer** | Society of Automotive Engineers (SAE International) | Standardizes commercial vehicle CAN bus frames (250 kbps, 29-bit identifiers, wheel speed, retarder status). | TWAI CAN Bus Adapter & Ingestion |
| **3. ISO 26262-3: Road Vehicles Functional Safety** | International Organization for Standardization (ISO) | Provides ASIL-D Hazard Analysis and Risk Assessment (HARA) guidelines for vehicle safety governors. | Tier-1 Safety Invariant & Failsafes |
| **4. BEML BH100 Haul Dumper Technical Spec** | Bharat Earth Movers Limited (BEML) | Provides actual mechanical mass (165.5 t loaded), braking buildup delays (0.25s), and 1,119 kW retarder curves. | Physics Engine & Retarder Solver |
| **5. NMDC Bailadila Deposit 5 Mining Plan** | National Mineral Development Corporation (NMDC Limited) | Official topographic survey of Kirandul/Bailadila ramps (8-12% grade, 22m radius hairpins, monsoon fog nowcasts). | 3D Digital Twin Geodata Mesh |
| **6. Haul Road Surface Friction Degradation** | E. F. Carter & G. H. Thompson, *Mining Engineering Science* | Quantifies wet clay slurry friction degradation ($\mu = 0.28\text{ to }0.35$) on iron ore mine haul roads. | Surface Friction Estimation Prior |
| **7. Receding-Horizon Fleet Pacing** | A. B. Borrelli et al., *IEEE Trans. Intell. Transp. Syst.* | Mathematical formulation of receding-horizon chance-constrained arrival pacing for heavy transport fleets. | Predictive Twin Decision Support |
