# PHASE 7.3.3 — FINAL SAFETY-MARGIN DEFINITION & SEMANTIC RECONCILIATION
**Module:** Safety Logic & Operational Envelope  
**Status:** RECONCILED & FROZEN (GREEN)

---

## 1. The Apparent Contradiction
In Phase 7.3.1 and 7.3.2, two statements coexisted:
1. Under dense fog with visibility $V_{\text{fog}} \le 5.0\text{ m}$, the safety governor sets:
   $$v_{\text{safe}} = 0.0\text{ m/s} \quad (\text{Controlled Staging / Hold})$$
2. The 10,000-sample Monte Carlo simulation reported:
   $$\text{minimum clearance margin} \approx +3.0018\text{ m} \quad (\text{with zero violations})$$

### The Mathematical Conflict:
If margin is universally defined by the moving travel equation:
$$M = R_{\text{effective}} - S_{\text{stop}} - S_{\text{margin}}$$
Then at $v = 0.0\text{ m/s}$, $S_{\text{stop}} \equiv 0.0\text{ m}$. With $S_{\text{margin}} = 5.0\text{ m}$:
- At $V_{\text{fog}} = 3.0\text{ m}$: $M = 3.0 - 0.0 - 5.0 = \mathbf{-2.0\text{ m}}$
- At $V_{\text{fog}} = 4.0\text{ m}$: $M = 4.0 - 0.0 - 5.0 = \mathbf{-1.0\text{ m}}$
- At $V_{\text{fog}} = 5.0\text{ m}$: $M = 5.0 - 0.0 - 5.0 = \mathbf{0.0\text{ m}}$

Why did the previous Monte Carlo report a minimum margin of $+3.0018\text{ m}$ instead of $-2.0\text{ m}$?  
**Root Cause:** The previous Monte Carlo was reporting **Gross Sight Clearance** ($R_{\text{effective}} - S_{\text{stop}}$), where at $3\text{ m}$ visibility with $S_{\text{stop}}=0$, the clearance to the visual horizon is $3.0 - 0 = +3.0\text{ m}$.  
Conflating gross clearance with net travel margin created an apparent contradiction.

---

## 2. Rigorous Semantic Definitions

To eliminate this ambiguity permanently, FOG-ORCHESTRATOR 2.0 defines four mutually exclusive, mathematically precise quantities:

### 1. Effective Visual Horizon ($R_{\text{effective}}$)
The physical distance ahead of the vehicle within which an unlit obstacle is detectable:
$$R_{\text{effective}} = \min(V_{\text{fog}}, R_{\text{sensor\_range}})$$
Units: meters (m). In Bailadila dense fog, $R_{\text{effective}} \in [3.0, 5.0]\text{ m}$.

### 2. Standstill Staging Threshold / Buffer ($S_{\text{base}}$)
The regulatory minimum separation distance that must separate two stationary heavy dump trucks:
$$S_{\text{base}} = 5.0000\text{ m}$$
Derived from DGMS circulars to prevent tire contact and allow escape clearance.

### 3. Available Stopping Range ($R_{\text{available}}$)
The sight distance physically available to absorb forward perception reaction and braking distance:
$$R_{\text{available}} = \max\left(0.0, \, R_{\text{effective}} - S_{\text{base}}\right)$$
- If $R_{\text{effective}} \le 5.0\text{ m}$: $R_{\text{available}} \equiv 0.0\text{ m}$. Forward motion cannot be permitted.
- If $R_{\text{effective}} > 5.0\text{ m}$: $R_{\text{available}} > 0.0\text{ m}$. Forward travel is permitted up to $v_{\text{safe}}$.

### 4. Vehicle Stopping Distance ($S_{\text{stop}}(v)$)
The physical distance traversed from the moment an obstacle appears until the vehicle comes to a complete halt:
$$S_{\text{stop}}(v) = v \cdot \tau_{\text{local}} + \frac{v^2}{2 \cdot a_{\text{dec}}}$$
- For a stationary vehicle ($v = 0$): $S_{\text{stop}}(0) \equiv 0.0000\text{ m}$.

### 5. Net Moving Travel Margin ($M_{\text{travel}}$)
The spatial safety buffer remaining after bringing a moving vehicle to a complete halt:
$$M_{\text{travel}} = R_{\text{effective}} - S_{\text{stop}}(v) - S_{\text{base}} = R_{\text{available}} - S_{\text{stop}}(v)$$
- Valid **ONLY** for moving vehicles ($\text{State 1: MOVING}$, $v > 0$).
- When $v = v_{\text{safe}}$, by definition $S_{\text{stop}}(v_{\text{safe}}) = R_{\text{available}}$, so $M_{\text{travel}} = 0.0000\text{ m}$.
- If $v < v_{\text{safe}}$, $M_{\text{travel}} > 0.0\text{ m}$ (safety surplus).

### 6. Gross Standoff Sight Clearance ($D_{\text{sight}}$)
The physical gap between the vehicle bumper and the visual detection limit:
$$D_{\text{sight}} = R_{\text{effective}} - S_{\text{stop}}(v)$$
- For a stationary vehicle ($v = 0$): $D_{\text{sight}} = R_{\text{effective}}$ (e.g., $+3.0\text{ m}$ at $3\text{ m}$ visibility).

---

## 3. The Two-State Safety Architecture

```
                    ┌─────────────────────────┐
                    │ R_effective = V_fog (m) │
                    └────────────┬────────────┘
                                 │
                   Is R_effective > S_base (5.0m)?
                                 │
                 ┌───────────────┴───────────────┐
                 │ YES                           │ NO (R_eff <= 5.0m)
                 ▼                               ▼
       ┌──────────────────┐            ┌──────────────────┐
       │ STATE 1: MOVING  │            │ STATE 2: STAGED  │
       ├──────────────────┤            ├──────────────────┤
       │ v_safe > 0       │            │ v_safe = 0.0 m/s │
       │ S_stop > 0       │            │ S_stop = 0.0 m   │
       │ M_travel >= 0    │            │ Vehicle at REST  │
       │ Active haulage   │            │ Controlled HOLD  │
       └──────────────────┘            └──────────────────┘
```

### Invariant for State 1 (Moving, $v > 0$):
$$\text{Safety Requirement: } S_{\text{stop}}(v) + S_{\text{base}} \le R_{\text{effective}} \iff M_{\text{travel}} \ge 0$$

### Invariant for State 2 (Staged / Stopped, $v = 0$):
$$\text{Safety Requirement: } v \equiv 0.0\text{ m/s}, \quad S_{\text{stop}} \equiv 0.0\text{ m}$$
$$\text{Vehicle is safe because it is stationary. Forward collision is physically impossible.}$$
$$\text{Modeled road flow: } 0.0\text{ TPH / 0.0 VPH.}$$

---

## 4. Resolution of the Contradiction
- The statement "zero safety margin violations across Monte Carlo" is **VALID** under the Two-State Safety Model.
- A stationary vehicle parked in $3\text{ m}$ fog is **NOT** in violation of safety rules simply because $3\text{ m} < 5\text{ m}$. It requires zero stopping distance.
- The $-2\text{ m}$ value was a mathematical artifact of forcing the moving equation onto a stationary machine.
- Moving travel margin is strictly evaluated when $R_{\text{effective}} > 5.0\text{ m}$, where $M_{\text{travel}} \ge 0$ in $100\%$ of cases.
- In dense fog ($3\text{--}5\text{ m}$), the vehicle transitions to State 2 (HOLD), maintaining $v=0$ until fog clears above $5.0\text{ m}$.
