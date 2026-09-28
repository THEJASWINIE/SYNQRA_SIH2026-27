import time
import requests
import json
from fog_safe.safety import solve_safe_speed
from hardware_emulator import VehicleHardwareEmulator
from integration_adapters.twin_velocity_adapter import TwinVelocityAdapter

def benchmark_fog_closed_loop():
    truck = VehicleHardwareEmulator('TRUCK_01', initial_position=0.0)
    adapter = TwinVelocityAdapter(prototype_scale=0.10)

    print("=== ADVERSARIAL ATTACK 6: FOG CLOSED LOOP ===")
    print("Classification: INJECTED ENVIRONMENTAL INPUT (Not Physical Fog)")
    visibility_input = 15.0 # meters

    t0 = time.perf_counter()
    truck.update_environment(visibility_m=visibility_input, friction_mu=0.35, grade_pct=0.0)
    t_twin = time.perf_counter()

    res_physics = solve_safe_speed(
        vehicle=truck.phys_vehicle,
        road=truck.road,
        env=truck.env,
        comm=truck.comm,
        mu_effective=truck.env.mu_true,
        r_effective=truck.env.r_effective
    )
    t_solver = time.perf_counter()

    cmd = adapter.format_velocity_command(
        vehicle_id='TRUCK_01',
        computed_velocity=res_physics.v_safe_ms,
        timestamp=time.time(),
        validity=True,
        apply_scaling=True,
        apply_ramping=True
    )
    t_cmd = time.perf_counter()

    governor_safe_mps = min(cmd['prototype_target_ms'], 0.50)
    t_gov = time.perf_counter()

    motor_pwm = int((governor_safe_mps / 0.50) * 150) if governor_safe_mps > 0 else 0
    t_motor = time.perf_counter()

    r = requests.get('http://127.0.0.1:8000/api/vehicles', timeout=2)
    t_hmi = time.perf_counter()

    dt_twin_us = (t_twin - t0) * 1e6
    dt_solver_us = (t_solver - t_twin) * 1e6
    dt_cmd_us = (t_cmd - t_solver) * 1e6
    dt_gov_us = (t_gov - t_cmd) * 1e6
    dt_motor_us = (t_motor - t_gov) * 1e6
    dt_hmi_ms = (t_hmi - t_motor) * 1e3
    total_comp_ms = (t_motor - t0) * 1e3

    print(f"T_env injection: {visibility_input} m")
    print(f"T_twin update:   {dt_twin_us:.1f} us")
    print(f"T_solver solve:  {dt_solver_us:.1f} us (v_safe={res_physics.v_safe_ms:.3f} m/s)")
    print(f"T_command gen:   {dt_cmd_us:.1f} us (target={cmd['prototype_target_ms']:.3f} m/s)")
    print(f"T_governor eval: {dt_gov_us:.1f} us (governed={governor_safe_mps:.3f} m/s)")
    print(f"T_motor PWM map: {dt_motor_us:.1f} us (PWM={motor_pwm})")
    print(f"T_hmi query:     {dt_hmi_ms:.2f} ms")
    print(f"TOTAL COMPUTATIONAL LATENCY (Env -> Motor): {total_comp_ms:.3f} ms")
    print(f"TOTAL LATENCY INCLUDING HMI REST ROUND-TRIP: {(t_hmi - t0)*1e3:.3f} ms")
    print("RF AIRTIME CONSTANT (Semtech SX1278 PHY): 38.5 ms (PHYSICAL RF AIRTIME COMPONENT ONLY)")

if __name__ == '__main__':
    benchmark_fog_closed_loop()
