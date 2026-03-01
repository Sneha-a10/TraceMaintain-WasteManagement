# -*- coding: utf-8 -*-
"""
sensor_simulation.py
====================
Smart Campus Wastewater Monitoring System
Sensor Simulation Layer

Regulatory References:
  - Environment Protection Rules (General Effluent Standards) — Schedule VI
  - CPCB OCEMS (Online Continuous Effluent Monitoring System) Guidelines

Parameters simulated:
  pH              : effluent pH
  BOD             : Biochemical Oxygen Demand (mg/L)
  COD             : Chemical Oxygen Demand (mg/L)
  TSS             : Total Suspended Solids (mg/L)
  Ammonical N     : Ammonical Nitrogen (mg/L)
  Oil & Grease    : Oil & Grease (mg/L)
  Flow Rate       : m3/hour (OCEMS requirement)
  Temperature     : °C     (OCEMS requirement)

NOTE: This module ONLY generates raw telemetry.
      No regulatory limit comparison or compliance logic lives here.
      Violation detection is handled by the downstream reasoning module.
"""

import random
import math
from datetime import datetime, timezone

# ============================================================================
# NORMAL OPERATING RANGES (realistic compliant steady-state baselines)
# ============================================================================
NORMAL_RANGES = {
    "pH":               {"base": 7.2,  "noise_std": 0.15},
    "BOD_mg_L":         {"base": 18.0, "noise_std": 2.5},
    "COD_mg_L":         {"base": 140.0,"noise_std": 12.0},
    "TSS_mg_L":         {"base": 55.0, "noise_std": 6.0},
    "ammonical_N_mg_L": {"base": 22.0, "noise_std": 3.0},
    "oil_grease_mg_L":  {"base": 5.0,  "noise_std": 0.8},
    "temperature_C":    {"base": 30.0, "noise_std": 1.5},
    "flow_rate_m3_hr":  {"base": 80.0, "noise_std": 8.0},
}


# ============================================================================
# SIGNAL GENERATORS
# ============================================================================

def _gaussian_noise(std: float) -> float:
    """Returns Gaussian noise with zero mean."""
    return random.gauss(0, std)


def _diurnal_cycle(elapsed_seconds: float, amplitude: float, period_hours: float = 24.0) -> float:
    """
    Simulates a sinusoidal diurnal (daily) cycle.
    Peaks at midday, troughs at midnight — realistic for campus STP.
    """
    period_sec = period_hours * 3600
    return amplitude * math.sin(2 * math.pi * elapsed_seconds / period_sec)


def generate_pH(elapsed_seconds: float, drift: float = 0.0) -> float:
    """
    Generate a realistic pH reading.
    - Slight diurnal variation (biological activity peaks midday)
    - Gaussian noise
    - Optional drift for degradation scenarios
    """
    base = NORMAL_RANGES["pH"]["base"]
    noise = _gaussian_noise(NORMAL_RANGES["pH"]["noise_std"])
    cycle = _diurnal_cycle(elapsed_seconds, amplitude=0.1, period_hours=12.0)
    value = base + noise + cycle + drift
    return round(value, 2)


def generate_BOD(elapsed_seconds: float, drift: float = 0.0) -> float:
    base = NORMAL_RANGES["BOD_mg_L"]["base"]
    noise = _gaussian_noise(NORMAL_RANGES["BOD_mg_L"]["noise_std"])
    cycle = _diurnal_cycle(elapsed_seconds, amplitude=2.0)
    value = base + noise + cycle + drift
    return round(max(0.0, value), 2)


def generate_COD(elapsed_seconds: float, drift: float = 0.0) -> float:
    base = NORMAL_RANGES["COD_mg_L"]["base"]
    noise = _gaussian_noise(NORMAL_RANGES["COD_mg_L"]["noise_std"])
    cycle = _diurnal_cycle(elapsed_seconds, amplitude=8.0)
    value = base + noise + cycle + drift
    return round(max(0.0, value), 2)


def generate_TSS(elapsed_seconds: float, drift: float = 0.0) -> float:
    base = NORMAL_RANGES["TSS_mg_L"]["base"]
    noise = _gaussian_noise(NORMAL_RANGES["TSS_mg_L"]["noise_std"])
    cycle = _diurnal_cycle(elapsed_seconds, amplitude=4.0)
    value = base + noise + cycle + drift
    return round(max(0.0, value), 2)


def generate_ammonical_N(elapsed_seconds: float, drift: float = 0.0) -> float:
    base = NORMAL_RANGES["ammonical_N_mg_L"]["base"]
    noise = _gaussian_noise(NORMAL_RANGES["ammonical_N_mg_L"]["noise_std"])
    value = base + noise + drift
    return round(max(0.0, value), 2)


def generate_oil_grease(elapsed_seconds: float, drift: float = 0.0) -> float:
    base = NORMAL_RANGES["oil_grease_mg_L"]["base"]
    noise = _gaussian_noise(NORMAL_RANGES["oil_grease_mg_L"]["noise_std"])
    value = base + noise + drift
    return round(max(0.0, value), 2)


def generate_temperature(elapsed_seconds: float, drift: float = 0.0) -> float:
    base = NORMAL_RANGES["temperature_C"]["base"]
    noise = _gaussian_noise(NORMAL_RANGES["temperature_C"]["noise_std"])
    cycle = _diurnal_cycle(elapsed_seconds, amplitude=2.0)
    value = base + noise + cycle + drift
    return round(value, 1)


def generate_flow_rate(elapsed_seconds: float, drift: float = 0.0) -> float:
    """
    Flow rate follows a strong diurnal pattern:
    - Peak during morning + evening usage hours
    - Low at night
    Uses a double-hump approximation via two sinusoids.
    """
    base = NORMAL_RANGES["flow_rate_m3_hr"]["base"]
    noise = _gaussian_noise(NORMAL_RANGES["flow_rate_m3_hr"]["noise_std"])
    # Morning hump (period ~12h) + evening hump
    morning = 25.0 * math.sin(2 * math.pi * elapsed_seconds / (12 * 3600))
    evening = 15.0 * math.sin(2 * math.pi * elapsed_seconds / (8 * 3600))
    value = base + noise + morning + evening + drift
    return round(max(0.0, value), 2)


def generate_total_volume(flow_rate_m3_hr: float, interval_seconds: float = 5.0) -> float:
    """
    Cumulative effluent volume contributed in this interval.
    V = flow_rate (m3/hr) * interval_hr
    """
    interval_hr = interval_seconds / 3600.0
    return round(flow_rate_m3_hr * interval_hr, 4)


# ============================================================================
# WASTWATER ASSET CLASS
# ============================================================================

class WastewaterAsset:
    """
    Represents a single campus wastewater asset (e.g., Hostel STP, Canteen STP).

    Attributes
    ----------
    asset_id        : Unique identifier string (e.g., "STP_HOSTEL_A")
    flow_rate       : Current flow rate in m3/hour
    pH              : Current pH reading
    BOD             : Biochemical Oxygen Demand in mg/L
    COD             : Chemical Oxygen Demand in mg/L
    TSS             : Total Suspended Solids in mg/L
    ammonical_N     : Ammonical Nitrogen in mg/L
    oil_grease      : Oil & Grease in mg/L
    temperature     : Effluent temperature in °C
    total_volume    : Cumulative volume discharged in m3
    elapsed_seconds : Simulation clock (seconds since start)
    _drifts         : Internal dict of per-parameter drift offsets
    """

    def __init__(self, asset_id: str, sampling_interval: float = 5.0):
        self.asset_id = asset_id
        self.sampling_interval = sampling_interval  # seconds

        # Sensor readings (initialised at nominal baselines)
        self.flow_rate   = NORMAL_RANGES["flow_rate_m3_hr"]["base"]
        self.pH          = NORMAL_RANGES["pH"]["base"]
        self.BOD         = NORMAL_RANGES["BOD_mg_L"]["base"]
        self.COD         = NORMAL_RANGES["COD_mg_L"]["base"]
        self.TSS         = NORMAL_RANGES["TSS_mg_L"]["base"]
        self.ammonical_N = NORMAL_RANGES["ammonical_N_mg_L"]["base"]
        self.oil_grease  = NORMAL_RANGES["oil_grease_mg_L"]["base"]
        self.temperature = NORMAL_RANGES["temperature_C"]["base"]
        self.total_volume = 0.0

        # Simulation clock
        self.elapsed_seconds = 0.0

        # Per-parameter drift (used by scenario engine)
        self._drifts = {
            "pH":               0.0,
            "BOD_mg_L":         0.0,
            "COD_mg_L":         0.0,
            "TSS_mg_L":         0.0,
            "ammonical_N_mg_L": 0.0,
            "oil_grease_mg_L":  0.0,
            "temperature_C":    0.0,
            "flow_rate_m3_hr":  0.0,
        }

        # Active scenario name (for metadata tagging in output)
        self.active_scenario: str = "NORMAL"

    # ------------------------------------------------------------------ #
    #  Core state update                                                   #
    # ------------------------------------------------------------------ #
    def update_state(self) -> None:
        """
        Advance the simulation by one sampling interval.
        Regenerates all sensor readings using signal generators.
        """
        t = self.elapsed_seconds

        self.flow_rate   = generate_flow_rate(t,    self._drifts["flow_rate_m3_hr"])
        self.pH          = generate_pH(t,            self._drifts["pH"])
        self.BOD         = generate_BOD(t,           self._drifts["BOD_mg_L"])
        self.COD         = generate_COD(t,           self._drifts["COD_mg_L"])
        self.TSS         = generate_TSS(t,           self._drifts["TSS_mg_L"])
        self.ammonical_N = generate_ammonical_N(t,   self._drifts["ammonical_N_mg_L"])
        self.oil_grease  = generate_oil_grease(t,    self._drifts["oil_grease_mg_L"])
        self.temperature = generate_temperature(t,   self._drifts["temperature_C"])

        # Accumulate volume
        self.total_volume += generate_total_volume(self.flow_rate, self.sampling_interval)

        # Advance time
        self.elapsed_seconds += self.sampling_interval

    # ------------------------------------------------------------------ #
    #  Anomaly injection                                                   #
    # ------------------------------------------------------------------ #
    def simulate_anomaly(self, scenario: str, **kwargs) -> None:
        """
        Inject a violation / anomaly scenario by adjusting drift offsets.
        Delegates to the scenario_engine. This method is the hook.

        Parameters
        ----------
        scenario : str
            One of: "pH_DRIFT", "COD_GRADUAL", "BOD_SPIKE",
                    "TSS_OVERLOAD", "FLOW_SURGE", "NORMAL"
        kwargs   : Additional parameters passed to the scenario engine.
        """
        # Handled externally by ScenarioEngine; this simply records the name.
        self.active_scenario = scenario

    def reset_drifts(self) -> None:
        """Clears all drift offsets — returns asset to normal behaviour."""
        for key in self._drifts:
            self._drifts[key] = 0.0
        self.active_scenario = "NORMAL"

    # ------------------------------------------------------------------ #
    #  Output serialisation — raw telemetry only                          #
    # ------------------------------------------------------------------ #
    def to_json(self) -> dict:
        """
        Serialises the current sensor state to a raw CPCB OCEMS telemetry packet.
        Contains only measured physical values — no compliance fields.
        """
        return {
            "asset_id":         self.asset_id,
            "timestamp":        datetime.now(timezone.utc).isoformat(),
            "scenario":         self.active_scenario,
            "flow_rate_m3_hr":  self.flow_rate,
            "total_volume_m3":  round(self.total_volume, 4),
            "pH":               self.pH,
            "BOD_mg_L":         self.BOD,
            "COD_mg_L":         self.COD,
            "TSS_mg_L":         self.TSS,
            "ammonical_N_mg_L": self.ammonical_N,
            "oil_grease_mg_L":  self.oil_grease,
            "temperature_C":    self.temperature,
        }

    def __repr__(self) -> str:
        return (
            f"WastewaterAsset(id={self.asset_id}, scenario={self.active_scenario}, "
            f"pH={self.pH}, COD={self.COD}, flow={self.flow_rate})"
        )
