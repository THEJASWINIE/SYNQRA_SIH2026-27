# PHASE 7.3.4 — ATTACK #2: EMERGENCY DECELERATION RE-DERIVATION & SENSITIVITY
**Module:** Vehicle Longitudinal Dynamics  
**Dataset:** `data/phase7_3_4_deceleration_sensitivity.csv`  
**Classification:** **DERIVED MODEL PARAMETER (GREEN / YELLOW CONDITIONAL)**  

---

## 1. Independent First-Principles Re-Derivation

Using an independent calculator (`experiments/run_phase7_3_4_independent_physics.py`) completely decoupled from the `fog_safe` codebase:

### Canonical Parameter Set:
- Gross Mass: $m = 165,500.0\text{ kg}$
- Civil Ramp Grade: $G = -8.0\%$ ($\theta = \arctan(0.08) = 0.079830\text{ rad}$)
- Standard Gravity: $g = 9.80665\text{ m/s}^2$
- Rolling Resistance Coefficient: $C_{\text{rr}} = 0.025$
- Road Friction: $\mu = 0.35$
- Rated Mechanical Rim Force: $F_{\text{brake}} = 550,000.0\text{ N}$

$$\cos\theta = 0.996815, \quad \sin\theta = 0.079745$$
$$F_{\text{norm}} = 165500 \times 9.80665 \times 0.996815 = 1,617,831.8\text{ N}$$
$$F_{\text{roll}} = 0.025 \times 1,617,831.8 = 40,445.8\text{ N}$$
$$F_{\text{grade\_forward}} = 165500 \times 9.80665 \times 0.079745 = 129,426.5\text{ N}$$
$$F_{\text{net}} = 550,000.0 + 40,445.8 - 129,426.5 = \mathbf{461,019.3\text{ N}}$$
$$a_{\text{canonical}} = \frac{461,019.3\text{ N}}{165,500\text{ kg}} = \mathbf{2.785615\text{ m/s}^2} \approx \mathbf{2.7856\text{ m/s}^2}$$

### Legacy Parameter Set:
- Gross Mass: $m = 165,000.0\text{ kg}$
- Standard Gravity: $g = 9.81000\text{ m/s}^2$
- Rolling Resistance Coefficient: $C_{\text{rr}} = 0.020$
- Downhill Gravity Component: $F_{\text{grade}} = 129,079.3\text{ N}$
- Rolling Resistance Force: $F_{\text{roll}} = 32,269.9\text{ N}$
$$F_{\text{net}} = 550,000.0 + 32,269.9 - 129,079.3 = \mathbf{453,190.6\text{ N}}$$
$$a_{\text{legacy}} = \frac{453,190.6\text{ N}}{165,000\text{ kg}} = \mathbf{2.746609\text{ m/s}^2} \approx \mathbf{2.7466\text{ m/s}^2}$$

---

## 2. Deceleration Sensitivity Grid (320 Parameter Combinations)

To determine whether emergency deceleration is robust or fragile, an independent sensitivity grid was executed across 320 combinations of mass ($150\text{--}180\text{ t}$), grade ($-3\%$ to $-10\%$), rolling resistance ($0.015\text{--}0.030$), and friction ($0.20\text{--}0.40$).

### Representative Sensitivity Excerpts:

| Mass ($m$) | Grade ($G$) | Rolling Res ($C_{\text{rr}}$) | Friction ($\mu$) | Net Retarding Force ($F_{\text{net}}$) | Deceleration ($a_{\text{net}}$) | Governing Regime |
|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| $150,000\text{ kg}$ | $-8.0\%$ | $0.025$ | $0.35$ | $449,949.5\text{ N}$ | **3.0000 m/s²** | Brake-Force Limited |
| $165,500\text{ kg}$ | $-3.0\%$ | $0.025$ | $0.35$ | $541,617.5\text{ N}$ | **3.2726 m/s²** | Brake-Force Limited |
| $165,500\text{ kg}$ | $-5.0\%$ | $0.025$ | $0.35$ | $509,248.5\text{ N}$ | **3.0770 m/s²** | Brake-Force Limited |
| **165,500 kg** | **-8.0%** | **0.025** | **0.35** | **461,019.3 N** | **2.7856 m/s²** | **CANONICAL BASELINE** |
| $165,500\text{ kg}$ | $-10.0\%$ | $0.025$ | $0.35$ | $429,203.4\text{ N}$ | **2.5934 m/s²** | Brake-Force Limited |
| $180,000\text{ kg}$ | $-8.0\%$ | $0.025$ | $0.35$ | $453,230.1\text{ N}$ | **2.5180 m/s²** | Brake-Force Limited |
| $165,500\text{ kg}$ | $-8.0\%$ | $0.015$ | $0.35$ | $444,841.0\text{ N}$ | **2.6879 m/s²** | Brake-Force Limited |
| $165,500\text{ kg}$ | $-8.0\%$ | $0.030$ | $0.35$ | $469,108.5\text{ N}$ | **2.8345 m/s²** | Brake-Force Limited |
| $165,500\text{ kg}$ | $-8.0\%$ | $0.025$ | **0.20** | $234,614.3\text{ N}$ | **1.4176 m/s²** | **TRACTION LIMITED** |
| $165,500\text{ kg}$ | $-8.0\%$ | $0.025$ | **0.25** | $315,505.9\text{ N}$ | **1.9064 m/s²** | **TRACTION LIMITED** |
| $165,500\text{ kg}$ | $-8.0\%$ | $0.025$ | **0.30** | $396,397.5\text{ N}$ | **2.3952 m/s²** | **TRACTION LIMITED** |

---

## 3. Hostile Technical Assessment

1. **Robustness Under Normal Friction ($\mu \ge 0.35$):**
   - Deceleration varies between $2.52\text{ m/s}^2$ ($180\text{ t}$ overload on $-8\%$ ramp) and $3.27\text{ m/s}^2$ (on flatter $-3\%$ benches).
   - The canonical value of $2.7856\text{ m/s}^2$ is a centrally robust representation of a loaded dumper on $-8\%$ grade.
2. **Extreme Sensitivity to Friction Degradation ($\mu < 0.34$):**
   - If monsoon rain creates liquid hematite slime ($\mu = 0.25$), net deceleration plummets by **$-31.6\%$** to $1.9064\text{ m/s}^2$.
   - At $\mu = 0.20$, deceleration drops to $1.4176\text{ m/s}^2$ (**$-49.1\%$** reduction).
3. **Classification of 2.7466 vs 2.7856 m/s²:**
   - **$2.7466\text{ m/s}^2$** is the **LEGACY/CONSERVATIVE DERIVED SCENARIO** ($165.0\text{ t}$, $C_{\text{rr}}=0.020$). It is retained in the safety governor because lower assumed deceleration is **conservative** (demands longer stopping distance, producing a slightly lower, safer permitted speed: $5.1158\text{ m/s}$ vs $5.1328\text{ m/s}$).
   - **$2.7856\text{ m/s}^2$** is the **CANONICAL PHYSICAL VALUE** reflecting $165.5\text{ t}$ GVW, $C_{\text{rr}}=0.025$, and standard gravity $g=9.80665\text{ m/s}^2$.
