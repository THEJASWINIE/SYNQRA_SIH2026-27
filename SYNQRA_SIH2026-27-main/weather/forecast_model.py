import numpy as np

class ForecastModel:
    """
    Generates environmental and visibility forecasts over a planning horizon.
    Supports perfect forecasting, biased forecasting, and spatial-temporal fog drift.
    """
    def __init__(self, horizon_s: float, step_s: float):
        self.horizon_s = horizon_s
        self.step_s = step_s
        self.num_steps = int(horizon_s / step_s)

    def generate_forecast(self, current_time: float, current_visibility: float, 
                          scenario_name: str, error_pct: float = 0.0) -> np.ndarray:
        """
        Generate visibility forecast array over the planning horizon.
        error_pct introduces forecast bias (e.g., +20% or -20% offset).
        """
        forecast = np.zeros(self.num_steps)
        
        # Populate forecast steps
        for i in range(self.num_steps):
            t_future = current_time + (i * self.step_s)
            
            # Predict visibility matching DEMO_06 weather profile
            if scenario_name == "clear":
                pred_vis = 50.0
            elif "DEMO_06" in scenario_name or "demo_06" in scenario_name or "demo" in scenario_name:
                # Replay profile
                if t_future < 300:
                    pred_vis = 50.0
                elif 300 <= t_future < 450:
                    frac = (t_future - 300.0) / 150.0
                    pred_vis = 50.0 - frac * 35.0
                elif 450 <= t_future < 1300:
                    pred_vis = 15.0
                else:
                    frac = min(1.0, (t_future - 1300.0) / 500.0)
                    pred_vis = 15.0 + frac * 35.0
            else:
                pred_vis = current_visibility
                
            # Apply forecast bias error
            pred_vis = pred_vis * (1.0 + error_pct)
            # Clamp to physical range [5.0, 50.0]
            forecast[i] = max(5.0, min(50.0, pred_vis))
            
        return forecast
