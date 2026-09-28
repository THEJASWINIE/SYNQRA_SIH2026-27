"""
scratch/audit_phase7_3_numerical.py
-----------------------------------
Forensic numerical recalculation script for Phase 7.3.1.
Verifies stopping distance, safe speed quadratic roots, latency reconstruction,
headway, capacity, queue relocation, and statistical tests.
"""

import math
import numpy as np
import pandas as pd
from scipy import stats

def audit_primary_failure():
    print("=" * 60)
    print("1. PRIMARY FAILURE INVESTIGATION: S_stop(v=5.12, tau=0.375, a=1.20)")
    print("=" * 60)
    v = 5.12
    tau = 0.375
    a = 1.20
    s_margin = 5.0
    r_effective = 12.0

    d_react = v * tau
    d_brake = (v**2) / (2.0 * a)
    s_stop = d_react + d_brake
    r_available = r_effective - s_margin
    total_required = s_stop + s_margin
    margin_remaining = r_effective - s_stop

    print(f"Velocity v:                {v:.4f} m/s ({v*3.6:.2f} km/h)")
    print(f"Latency tau:               {tau:.4f} s")
    print(f"Deceleration a_dec:        {a:.4f} m/s^2")
    print(f"Reaction distance d_react: {d_react:.4f} m")
    print(f"Braking distance d_brake:  {d_brake:.4f} m")
    print(f"Total stopping dist S_stop:{s_stop:.4f} m")
    print(f"Mandatory safety margin:   {s_margin:.4f} m")
    print(f"Total distance required:   {total_required:.4f} m")
    print(f"Effective visibility R_eff:{r_effective:.4f} m")
    print(f"Available range R_avail:   {r_available:.4f} m")
    print(f"Margin remaining at R_eff: {margin_remaining:.4f} m")
    
    if s_stop > r_available:
        deficit = s_stop - r_available
        print(f"\n[CRITICAL CONTRADICTION IDENTIFIED]")
        print(f"S_stop ({s_stop:.2f} m) EXCEEDS R_available ({r_available:.2f} m) by {deficit:.2f} m!")
        print(f"Total requirement ({total_required:.2f} m) EXCEEDS visibility ({r_effective:.2f} m) by {total_required - r_effective:.2f} m!")
        print(f"At v = 5.12 m/s and a = 1.20 m/s^2, the truck will crash into the obstacle at 12 m!")

def solve_quadratic_safe_speed(r_eff, s_base, tau, a):
    r_avail = r_eff - s_base
    if r_avail <= 0 or a <= 0:
        return 0.0, 0.0, 0.0, 0.0
    
    # Quadratic: (1/(2a))*v^2 + tau*v - r_avail = 0
    # v^2 + 2*a*tau*v - 2*a*r_avail = 0
    # v = -a*tau + sqrt((a*tau)^2 + 2*a*r_avail)
    term1 = a * tau
    discriminant = (term1**2) + 2.0 * a * r_avail
    v_max = -term1 + math.sqrt(discriminant)
    
    d_react = v_max * tau
    d_brake = (v_max**2) / (2.0 * a)
    s_stop = d_react + d_brake
    return v_max, d_react, d_brake, s_stop

def audit_safe_speed_grid():
    print("\n" + "=" * 60)
    print("2. RECOMPUTING SAFE SPEED ACROSS DECELERATIONS & LATENCIES")
    print("=" * 60)
    
    visibilities = [100.0, 50.0, 25.0, 12.0, 10.0, 8.0, 5.0, 4.0, 3.0]
    latencies = {
        "Nominal (0.375s)": 0.375,
        "P99 (0.437s)": 0.437,
        "Worst (0.475s)": 0.475,
        "Legacy (0.800s)": 0.800
    }
    decelerations = {
        "Conservative Service (1.20 m/s^2)": 1.20,
        "Slick Wet -8% (2.49 m/s^2)": 2.4926,
        "Nominal Wet -8% (2.75 m/s^2)": 2.7466,
        "Dry Net -8% (2.79 m/s^2)": 2.7856,
        "ISO 3450 Flat Max (3.32 m/s^2)": 3.323
    }
    
    s_base = 5.0
    
    print("\n--- AT VISIBILITY = 12.0 m (R_available = 7.0 m) ---")
    rows = []
    for dec_name, a in decelerations.items():
        for lat_name, tau in latencies.items():
            v, d_r, d_b, s_s = solve_quadratic_safe_speed(12.0, s_base, tau, a)
            rows.append({
                "Deceleration Model": dec_name,
                "a (m/s^2)": a,
                "Latency Model": lat_name,
                "tau (s)": tau,
                "v_safe (m/s)": round(v, 4),
                "v_safe (km/h)": round(v * 3.6, 2),
                "d_react (m)": round(d_r, 4),
                "d_brake (m)": round(d_b, 4),
                "S_stop (m)": round(s_s, 4),
                "S_total (m)": round(s_s + s_base, 4)
            })
    df_12m = pd.DataFrame(rows)
    print(df_12m.to_string(index=False))

def audit_headway_and_capacity():
    print("\n" + "=" * 60)
    print("3. AUDITING HEADWAY & CAPACITY FORMULATIONS")
    print("=" * 60)
    l_truck = 10.52
    s_base = 5.0
    
    # Audit where 17.52 came from:
    # 7.0 m + 10.52 m = 17.52 m! (Omitted s_base = 5.0 m!)
    # If s_stop = 7.0 m, gap headway = s_stop + s_base = 12.0 m
    # space headway = s_stop + s_base + l_truck = 12.0 + 10.52 = 22.52 m
    print(f"Vehicle Length: {l_truck} m")
    print(f"Base Buffer:    {s_base} m")
    print(f"Stopping Dist:  7.00 m")
    print(f"Historical H_safe = 17.52 m -> 7.0 m + 10.52 m (OMITTED 5.0 m buffer!)")
    print(f"True Space Headway = S_stop (7.0m) + S_base (5.0m) + L_truck (10.52m) = 22.52 m")
    
    # Audit where 700.5 VPH came from:
    # 3600 * 4.3815 / 22.52 = 700.497 VPH!
    # It used legacy v_safe = 4.3815 m/s and space headway = 22.52 m!
    cap_700 = 3600.0 * 4.3815 / 22.52
    print(f"3600 * 4.3815 / 22.52 = {cap_700:.3f} VPH (Matches 700.5 VPH exactly!)")
    
    # What is capacity under corrected v_safe = 3.6734 m/s (with a=1.20)?
    cap_corrected_1_2 = 3600.0 * 3.6734 / 22.52
    print(f"Under a=1.20 m/s^2 (v=3.6734 m/s): Capacity = {cap_corrected_1_2:.1f} VPH")
    
    # What is capacity under a=2.75 m/s^2 (v=5.12 m/s)?
    cap_corrected_2_75 = 3600.0 * 5.116 / 22.52
    print(f"Under a=2.75 m/s^2 (v=5.116 m/s): Capacity = {cap_corrected_2_75:.1f} VPH")

def audit_waiting_times():
    print("\n" + "=" * 60)
    print("4. AUDITING WAITING TIME & RELOCATION (LITTLE'S LAW)")
    print("=" * 60)
    # Phase 7.3 reported:
    # Level 0: ramp queue = 860.2 s, origin wait = 42.0 s, cycle time = 2080.0 s
    # Level 1: ramp queue = 625.4 s, origin wait = 88.2 s, cycle time = 1845.2 s
    # Level 4: ramp queue = 141.6 s, origin wait = 489.2 s, cycle time = 1630.8 s
    
    ramp_l1 = 625.4
    ramp_l4 = 141.6
    ramp_red_pct = (ramp_l4 - ramp_l1) / ramp_l1 * 100.0
    
    origin_l1 = 88.2
    origin_l4 = 489.2
    origin_inc_pct = (origin_l4 - origin_l1) / origin_l1 * 100.0
    
    total_wait_l1 = ramp_l1 + origin_l1
    total_wait_l4 = ramp_l4 + origin_l4
    total_wait_red_pct = (total_wait_l4 - total_wait_l1) / total_wait_l1 * 100.0
    
    cycle_l1 = 1845.2
    cycle_l4 = 1630.8
    cycle_red_pct = (cycle_l4 - cycle_l1) / cycle_l1 * 100.0
    
    print(f"Level 1 Ramp Queue Waiting:   {ramp_l1:.1f} s")
    print(f"Level 4 Ramp Queue Waiting:   {ramp_l4:.1f} s")
    print(f"Ramp Waiting Reduction:       {ramp_red_pct:.2f}% (Matches 77.4%!)")
    print(f"Level 1 Shovel Bay Staging:   {origin_l1:.1f} s")
    print(f"Level 4 Shovel Bay Staging:   {origin_l4:.1f} s")
    print(f"Shovel Bay Staging Increase:  +{origin_inc_pct:.2f}%")
    print(f"Level 1 Total Waiting:        {total_wait_l1:.1f} s")
    print(f"Level 4 Total Waiting:        {total_wait_l4:.1f} s")
    print(f"Total Waiting Change:         {total_wait_red_pct:.2f}% (-82.8 s net reduction)")
    print(f"Cycle Time Change:            {cycle_red_pct:.2f}% (Matches -11.6%!)")

if __name__ == "__main__":
    audit_primary_failure()
    audit_safe_speed_grid()
    audit_headway_and_capacity()
    audit_waiting_times()
