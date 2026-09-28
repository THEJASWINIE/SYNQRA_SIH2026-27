# STAGE 5.2: CAPACITY HIERARCHY & BOTTLENECK ANALYSIS
**Mathematical Hierarchy: Road vs. Switchback vs. Shovel vs. Crusher vs. Fleet vs. Network**  
**Project:** FOG-ORCHESTRATOR 2.0 (SIH 2026-27 — NMDC Bailadila Iron Ore Haulage)  
**Status:** VALIDATED EVIDENCE — VERIFIED AGAINST DISCRETE-EVENT SIMULATOR STATE  

---

## 1. Mathematical Formulation & Hierarchy Definition

In large open-cast mines, total production is bounded by the physical law of minimum capacity across all serial infrastructure and fleet elements:

$$C_{\text{network}} = \min\left(C_{\text{road}}, C_{\text{switchback}}, C_{\text{shovel}}, C_{\text{crusher}}, C_{\text{fleet}}\right)$$

### 1.1 Element Definitions & Mathematical Models
1. **Kinematic Road Capacity ($C_{\text{road}}$):**
   $$h_{\text{safe}} = \frac{L_{\text{truck}} + d_{\text{standstill}} + v \tau_{\text{total}} + \frac{v^2}{2 a_{\text{dec}}}}{v}$$
   $$C_{\text{road}} = \frac{3600}{h_{\text{safe}}} \times \text{Payload} \quad [\text{TPH}]$$
2. **Switchback Bottleneck Capacity ($C_{\text{switchback}}$):**
   The switchback is a single-lane hairpin turn requiring alternating directional clearance:
   $$t_{\text{sb\_cycle}} = 2 \times \frac{L_{\text{switchback}}}{v_{\text{safe\_sb}}} + t_{\text{clearance\_buffer}}$$
   $$C_{\text{switchback}} = \frac{3600}{t_{\text{sb\_cycle}}} \times \text{Payload} \quad [\text{TPH}]$$
3. **Shovel Loading Capacity ($C_{\text{shovel}}$):**
   2 loading shovels at $15\text{ trucks/hr}$ each:
   $$C_{\text{shovel}} = 2 \times 15 \times 91.5\text{ t} = 2{,}745.0\text{ TPH}$$
4. **Crusher Service Capacity ($C_{\text{crusher}}$):**
   1 Primary Gyratory Crusher with a $200\text{ s}$ tipping/dump cycle ($18\text{ trucks/hr}$):
   $$C_{\text{crusher}} = 18 \times 91.5\text{ t} = 1{,}647.0\text{ TPH}$$
5. **Fleet Cycle Capacity ($C_{\text{fleet}}$):**
   Given fleet size $N$ and round-trip haul cycle time $t_{\text{cycle}}$:
   $$C_{\text{fleet}}(N) = N \times \left(\frac{3600}{t_{\text{cycle}}}\right) \times \text{Payload} \quad [\text{TPH}]$$

---

## 2. Capacity Hierarchy Matrix across Visibility and Fleet Sizes

Data logged in [`docs/STAGE5_2_CAPACITY_HIERARCHY.csv`](file:///c:/Users/JAGADEESH%20M/OneDrive/Documents/SIH-2026-27/docs/STAGE5_2_CAPACITY_HIERARCHY.csv):

| Visibility ($V$) | Fleet Size ($N$) | Safe Ramp Speed | Cycle Time ($t_{\text{cycle}}$) | $C_{\text{road}}$ | $C_{\text{switchback}}$ | $C_{\text{shovel}}$ | $C_{\text{crusher}}$ | $C_{\text{fleet}}$ | Physical Ceiling ($C_{\text{net}}$) | Active Physical Bottleneck |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **$100\text{ m}$** | 5 | $8.33\text{ m/s}$ | $1{,}196\text{ s}$ | $81{,}654\text{ TPH}$ | $4{,}989\text{ TPH}$ | $2{,}745\text{ TPH}$ | $1{,}647\text{ TPH}$ | **$1{,}377\text{ TPH}$** | **$1{,}377\text{ TPH}$** | `FLEET_CYCLE_CAPACITY (N=5)` |
| **$100\text{ m}$** | 10 | $8.33\text{ m/s}$ | $1{,}196\text{ s}$ | $81{,}654\text{ TPH}$ | $4{,}989\text{ TPH}$ | $2{,}745\text{ TPH}$ | **$1{,}647\text{ TPH}$** | $2{,}754\text{ TPH}$ | **$1{,}647\text{ TPH}$** | `CRUSHER_SERVICE_RATE (18 VPH)` |
| **$100\text{ m}$** | 20 | $8.33\text{ m/s}$ | $1{,}196\text{ s}$ | $81{,}654\text{ TPH}$ | $4{,}989\text{ TPH}$ | $2{,}745\text{ TPH}$ | **$1{,}647\text{ TPH}$** | $5{,}508\text{ TPH}$ | **$1{,}647\text{ TPH}$** | `CRUSHER_SERVICE_RATE (18 VPH)` |
| **$100\text{ m}$** | 50 | $8.33\text{ m/s}$ | $1{,}196\text{ s}$ | $81{,}654\text{ TPH}$ | $4{,}989\text{ TPH}$ | $2{,}745\text{ TPH}$ | **$1{,}647\text{ TPH}$** | $13{,}769\text{ TPH}$ | **$1{,}647\text{ TPH}$** | `CRUSHER_SERVICE_RATE (18 VPH)` |
| **$25\text{ m}$** | 5 | $8.33\text{ m/s}$ | $1{,}213\text{ s}$ | $80{,}133\text{ TPH}$ | $4{,}988\text{ TPH}$ | $2{,}745\text{ TPH}$ | $1{,}647\text{ TPH}$ | **$1{,}358\text{ TPH}$** | **$1{,}358\text{ TPH}$** | `FLEET_CYCLE_CAPACITY (N=5)` |
| **$25\text{ m}$** | 20 | $8.33\text{ m/s}$ | $1{,}213\text{ s}$ | $80{,}133\text{ TPH}$ | $4{,}988\text{ TPH}$ | $2{,}745\text{ TPH}$ | **$1{,}647\text{ TPH}$** | $5{,}432\text{ TPH}$ | **$1{,}647\text{ TPH}$** | `CRUSHER_SERVICE_RATE (18 VPH)` |
| **$12\text{ m}$** | 5 | $4.79\text{ m/s}$ | $1{,}649\text{ s}$ | $70{,}035\text{ TPH}$ | $2{,}889\text{ TPH}$ | $2{,}745\text{ TPH}$ | $1{,}647\text{ TPH}$ | **$999\text{ TPH}$** | **$999\text{ TPH}$** | `FLEET_CYCLE_CAPACITY (N=5)` |
| **$12\text{ m}$** | 20 | $4.79\text{ m/s}$ | $1{,}649\text{ s}$ | $70{,}035\text{ TPH}$ | $2{,}889\text{ TPH}$ | $2{,}745\text{ TPH}$ | **$1{,}647\text{ TPH}$** | $3{,}996\text{ TPH}$ | **$1{,}647\text{ TPH}$** | `CRUSHER_SERVICE_RATE (18 VPH)` |
| **$10\text{ m}$** | 5 | $3.93\text{ m/s}$ | $1{,}917\text{ s}$ | $63{,}105\text{ TPH}$ | $2{,}397\text{ TPH}$ | $2{,}745\text{ TPH}$ | $1{,}647\text{ TPH}$ | **$859\text{ TPH}$** | **$859\text{ TPH}$** | `FLEET_CYCLE_CAPACITY (N=5)` |
| **$10\text{ m}$** | 20 | $3.93\text{ m/s}$ | $1{,}917\text{ s}$ | $63{,}105\text{ TPH}$ | $2{,}397\text{ TPH}$ | $2{,}745\text{ TPH}$ | **$1{,}647\text{ TPH}$** | $3{,}437\text{ TPH}$ | **$1{,}647\text{ TPH}$** | `CRUSHER_SERVICE_RATE (18 VPH)` |
| **$8\text{ m}$** | 5 | $2.88\text{ m/s}$ | $2{,}464\text{ s}$ | $51{,}313\text{ TPH}$ | $1{,}783\text{ TPH}$ | $2{,}745\text{ TPH}$ | $1{,}647\text{ TPH}$ | **$669\text{ TPH}$** | **$669\text{ TPH}$** | `FLEET_CYCLE_CAPACITY (N=5)` |
| **$8\text{ m}$** | 10 | $2.88\text{ m/s}$ | $2{,}464\text{ s}$ | $51{,}313\text{ TPH}$ | $1{,}783\text{ TPH}$ | $2{,}745\text{ TPH}$ | $1{,}647\text{ TPH}$ | **$1{,}337\text{ TPH}$** | **$1{,}337\text{ TPH}$** | `FLEET_CYCLE_CAPACITY (N=10)` |
| **$8\text{ m}$** | 20 | $2.88\text{ m/s}$ | $2{,}464\text{ s}$ | $51{,}313\text{ TPH}$ | $1{,}783\text{ TPH}$ | $2{,}745\text{ TPH}$ | **$1{,}647\text{ TPH}$** | $2{,}674\text{ TPH}$ | **$1{,}647\text{ TPH}$** | `CRUSHER_SERVICE_RATE (18 VPH)` |
| **$\le 5\text{ m}$** | Any | **$0.00\text{ m/s}$** | **HALTED** | **$0\text{ TPH}$** | **$0\text{ TPH}$** | $2{,}745\text{ TPH}$ | $1{,}647\text{ TPH}$ | **$0\text{ TPH}$** | **$0\text{ TPH}$** | `TIER_1_SAFETY_ZERO_SPEED_HALT` |

---

## 3. Key Insights & Bottleneck Dynamics

1. **Kinematic Road Saturation is Never the Bottleneck:**
   At all viable speeds, $C_{\text{road}} > 50{,}000\text{ TPH}$. Haul roads can physically accommodate far more vehicles than service facilities can process. Theoretical road capacity calculations are meaningless for mine production planning.
2. **Small Fleets ($N=5$) are Truck-Constrained:**
   When only 5 dumpers operate, the crusher and shovels sit idle waiting for trucks. $C_{\text{network}} = C_{\text{fleet}} = 1{,}377\text{ TPH}$ under clear conditions and falls to $669\text{ TPH}$ at $8\text{ m}$ fog.
3. **Standard Fleets ($N \ge 20$) are Crusher-Constrained in Moderate Conditions:**
   With 20 dumpers, the fleet cycle capacity is $5{,}508\text{ TPH}$, far exceeding the single gyratory crusher's $1{,}647\text{ TPH}$ ($18\text{ VPH}$). Therefore, under clear and moderate fog ($V \ge 10\text{ m}$), the active physical bottleneck is the **Crusher Service Rate**.
4. **Switchback Capacity Degrades Linearly with Fog:**
   $C_{\text{switchback}}$ falls from $4{,}989\text{ TPH}$ at clear weather down to $1{,}783\text{ TPH}$ at $8\text{ m}$ fog. At $8\text{ m}$ fog, switchback capacity ($1{,}783\text{ TPH}$) approaches crusher capacity ($1{,}647\text{ TPH}$). If speed dropped slightly further, the switchback would overtake the crusher as the primary system bottleneck.
5. **Fog Extends Cycle Time, Shifting the Fleet Balance Point:**
   Under clear conditions, only 6 trucks are required to saturate the crusher ($6 \times 275\text{ TPH} = 1{,}650\text{ TPH}$). At $10\text{ m}$ fog ($t_{\text{cycle}} = 1{,}917\text{ s}$), 10 trucks are required to deliver the same rate. At $8\text{ m}$ fog ($t_{\text{cycle}} = 2{,}464\text{ s}$), 13 trucks are required.
