"""
Vehicle Model: Represents BEML BH100-class heavy dumper physical state.
"""

from fog_safe.config import VehicleParameters

class MiningVehicle:
    """
    Physical representation of BEML BH100 class mining haul dumper.
    """
    def __init__(self, params: VehicleParameters = None, is_loaded: bool = True):
        self.params = params if params is not None else VehicleParameters()
        self.is_loaded = is_loaded

    @property
    def mass(self) -> float:
        """Returns vehicle mass in kg depending on load state."""
        return self.params.mass_loaded if self.is_loaded else self.params.mass_empty

    @property
    def frontal_area(self) -> float:
        return self.params.frontal_area

    @property
    def Cd(self) -> float:
        return self.params.drag_coefficient

    @property
    def retarder_power_max(self) -> float:
        return self.params.retarder_power_max

    @property
    def hardware_brake_max(self) -> float:
        return self.params.hardware_brake_max_force

    def set_loaded_state(self, is_loaded: bool):
        self.is_loaded = is_loaded
