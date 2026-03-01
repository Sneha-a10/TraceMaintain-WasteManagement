# -*- coding: utf-8 -*-
"""
scenario_engine.py
==================
Smart Campus Wastewater Monitoring System
Violation Injection / Scenario Engine

Manages realistic violation scenarios based on CPCB/EPR non-compliance cases:
  - NORMAL               : Compliant steady operation
  - pH_DRIFT             : Gradual pH drift outside 5.5–9.0 range
  - COD_GRADUAL          : Slow COD rise toward and beyond 250 mg/L
  - BOD_SPIKE            : Sudden BOD spike event
  - TSS_OVERLOAD         : Suspended solids surge (e.g., rainstorm runoff)
  - FLOW_SURGE           : Sudden high-volume discharge (e.g., tank flush)
  - CONTAMINATION_SPIKE  : Multi-parameter sudden contamination event
  - GRADUAL_DEGRADATION  : Slow multi-parameter deterioration over time
"""

import random
import math


# ============================================================================
# SCENARIO REGISTRY
# Maps scenario name → description + violation target
# ============================================================================
SCENARIO_REGISTRY = {
    "NORMAL": {
        "description": "System operating within all regulatory limits.",
        "target_params": [],
    },
    "pH_DRIFT": {
        "description": "Gradual pH drift — acidic or alkaline exceedance.",
        "target_params": ["pH"],
    },
    "COD_GRADUAL": {
        "description": "Slow COD increase toward and beyond 250 mg/L.",
        "target_params": ["COD_mg_L"],
    },
    "BOD_SPIKE": {
        "description": "Sudden BOD spike event (e.g., canteen discharge).",
        "target_params": ["BOD_mg_L"],
    },
    "TSS_OVERLOAD": {
        "description": "Suspended solids overload (e.g., storm runoff, construction).",
        "target_params": ["TSS_mg_L"],
    },
    "FLOW_SURGE": {
        "description": "High-volume flow rate surge event (e.g., tank flush).",
        "target_params": ["flow_rate_m3_hr"],
    },
    "CONTAMINATION_SPIKE": {
        "description": "Multi-parameter spike from sudden contamination source.",
        "target_params": ["COD_mg_L", "BOD_mg_L", "oil_grease_mg_L"],
    },
    "GRADUAL_DEGRADATION": {
        "description": "Multi-parameter slow degradation — treatment plant underperformance.",
        "target_params": ["COD_mg_L", "BOD_mg_L", "TSS_mg_L", "ammonical_N_mg_L"],
    },
}


# ============================================================================
# SCENARIO ENGINE CLASS
# ============================================================================

class ScenarioEngine:
    """
    Manages the lifecycle of violation scenarios for a WastewaterAsset.

    Usage
    -----
    engine = ScenarioEngine(asset)
    engine.activate("pH_DRIFT")          # Start a scenario
    engine.step()                        # Advance scenario state each tick
    engine.deactivate()                  # Return to NORMAL
    """

    def __init__(self, asset):
        """
        Parameters
        ----------
        asset : WastewaterAsset
            The asset whose _drifts this engine will manipulate.
        """
        self.asset = asset
        self.active_scenario: str = "NORMAL"
        self._step_count: int = 0          # Ticks since scenario started
        self._scenario_config: dict = {}   # Internal config for active scenario

    # ------------------------------------------------------------------ #
    #  Activation / Deactivation                                          #
    # ------------------------------------------------------------------ #

    def activate(self, scenario: str) -> None:
        """
        Activate a named scenario. Resets step counter and configures params.

        Parameters
        ----------
        scenario : str
            Must be a key in SCENARIO_REGISTRY.
        """
        if scenario not in SCENARIO_REGISTRY:
            raise ValueError(
                f"Unknown scenario: '{scenario}'. "
                f"Available: {list(SCENARIO_REGISTRY.keys())}"
            )

        self.active_scenario = scenario
        self._step_count = 0
        self.asset.simulate_anomaly(scenario)

        # Configure scenario-specific parameters
        self._scenario_config = self._build_config(scenario)

        print(
            f"[ScenarioEngine] [START] Activated: {scenario} | "
            f"{SCENARIO_REGISTRY[scenario]['description']}"
        )

    def deactivate(self) -> None:
        """Return asset to normal operation."""
        self.active_scenario = "NORMAL"
        self._step_count = 0
        self._scenario_config = {}
        self.asset.reset_drifts()
        print("[ScenarioEngine] [STOP] Deactivated - returning to NORMAL.")

    # ------------------------------------------------------------------ #
    #  Per-tick step                                                       #
    # ------------------------------------------------------------------ #

    def step(self) -> None:
        """
        Called once per simulation tick BEFORE asset.update_state().
        Updates drift offsets on the asset based on the active scenario.
        """
        if self.active_scenario == "NORMAL":
            return

        handler = self._get_handler(self.active_scenario)
        handler(self._step_count, self._scenario_config)
        self._step_count += 1

    # ------------------------------------------------------------------ #
    #  Scenario Handlers                                                   #
    # ------------------------------------------------------------------ #

    def _handle_pH_drift(self, tick: int, config: dict) -> None:
        """
        Drift pH away from neutral.
        Direction: acidic (-) or alkaline (+), chosen at activation.
        Ramp: 0.005 units per tick (slow regulatory-realistic drift).
        Spike added at peak to simulate sudden acid/alkali dump.
        """
        direction = config.get("direction", 1)
        ramp_rate = 0.008         # units per tick
        max_drift  = config.get("max_drift", 3.5)

        # Ramp up drift linearly, cap at max
        drift = min(ramp_rate * tick * direction, max_drift * direction)

        # Random micro-spikes
        if random.random() < 0.08:
            drift += direction * random.uniform(0.2, 0.5)

        self.asset._drifts["pH"] = drift

    def _handle_COD_gradual(self, tick: int, config: dict) -> None:
        """
        Gradual COD increase — slow deterioration of treatment plant.
        Ramp: ~1.5 mg/L per tick, plateaus at 130 mg/L above baseline (≈270 total).
        """
        ramp_rate = 1.5
        max_drift = 130.0
        drift = min(ramp_rate * tick, max_drift)
        noise = random.gauss(0, 3.0)
        self.asset._drifts["COD_mg_L"] = drift + noise

    def _handle_BOD_spike(self, tick: int, config: dict) -> None:
        """
        Sudden BOD spike — square pulse decaying exponentially.
        Simulates a canteen or kitchen outlet discharge event.
        """
        # Peak immediately, decay with half-life ~20 ticks
        peak = config.get("peak", 45.0)    # mg/L above baseline
        half_life = 20
        decay = peak * math.exp(-0.693 * tick / half_life)

        noise = random.gauss(0, 1.5)
        self.asset._drifts["BOD_mg_L"] = max(0, decay + noise)

    def _handle_TSS_overload(self, tick: int, config: dict) -> None:
        """
        TSS overload from storm runoff or construction site.
        Fast ramp up, slow decay — like a turbidity cloud.
        """
        if tick < 10:
            # Ramp up sharply
            drift = tick * 8.0
        else:
            # Slow exponential decay
            drift = 80.0 * math.exp(-0.04 * (tick - 10))

        noise = random.gauss(0, 4.0)
        self.asset._drifts["TSS_mg_L"] = max(0, drift + noise)

    def _handle_flow_surge(self, tick: int, config: dict) -> None:
        """
        Flow rate surge — step change followed by gradual return to baseline.
        Simulates a storage tank flush or bypass event.
        """
        surge_amplitude = config.get("surge_amplitude", 280.0)  # m3/hr above baseline
        half_life = 30  # ticks

        if tick == 0:
            drift = surge_amplitude
        else:
            drift = surge_amplitude * math.exp(-0.693 * tick / half_life)

        noise = random.gauss(0, 5.0)
        self.asset._drifts["flow_rate_m3_hr"] = max(0, drift + noise)

        # Secondary: TSS goes up during surge (sediment resuspension)
        self.asset._drifts["TSS_mg_L"] = drift * 0.15

    def _handle_contamination_spike(self, tick: int, config: dict) -> None:
        """
        Multi-parameter spike — sudden contamination source (chemical dump, etc.).
        COD, BOD, and Oil & Grease all spike together.
        """
        half_life = 15
        cod_peak  = config.get("cod_peak",  160.0)
        bod_peak  = config.get("bod_peak",   20.0)
        oag_peak  = config.get("oag_peak",   12.0)

        decay = math.exp(-0.693 * tick / half_life)
        self.asset._drifts["COD_mg_L"]        = cod_peak * decay + random.gauss(0, 4)
        self.asset._drifts["BOD_mg_L"]        = bod_peak * decay + random.gauss(0, 2)
        self.asset._drifts["oil_grease_mg_L"] = oag_peak * decay + random.gauss(0, 0.5)

        # Slight pH drop (organic contamination is slightly acidic)
        self.asset._drifts["pH"] = -0.8 * decay

    def _handle_gradual_degradation(self, tick: int, config: dict) -> None:
        """
        All pollution parameters slowly rise — STP underperformance.
        Simulates biological treatment failure over hours/days.
        """
        ramp = min(tick * 0.8, 120.0)   # COD
        self.asset._drifts["COD_mg_L"]        = ramp        + random.gauss(0, 5)
        self.asset._drifts["BOD_mg_L"]        = ramp * 0.1  + random.gauss(0, 1.5)
        self.asset._drifts["TSS_mg_L"]        = ramp * 0.3  + random.gauss(0, 3)
        self.asset._drifts["ammonical_N_mg_L"]= ramp * 0.18 + random.gauss(0, 2)

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _get_handler(self, scenario: str):
        handlers = {
            "pH_DRIFT":             self._handle_pH_drift,
            "COD_GRADUAL":          self._handle_COD_gradual,
            "BOD_SPIKE":            self._handle_BOD_spike,
            "TSS_OVERLOAD":         self._handle_TSS_overload,
            "FLOW_SURGE":           self._handle_flow_surge,
            "CONTAMINATION_SPIKE":  self._handle_contamination_spike,
            "GRADUAL_DEGRADATION":  self._handle_gradual_degradation,
        }
        return handlers[scenario]

    def _build_config(self, scenario: str) -> dict:
        """Initialise randomised parameters for each scenario type."""
        if scenario == "pH_DRIFT":
            return {
                "direction":  random.choice([-1, 1]),    # acidic or alkaline
                "max_drift":  random.uniform(2.5, 4.0),  # how far it drifts
            }
        elif scenario == "BOD_SPIKE":
            return {
                "peak": random.uniform(45.0, 65.0),  # mg/L above baseline
            }
        elif scenario == "FLOW_SURGE":
            return {
                "surge_amplitude": random.uniform(200.0, 380.0),
            }
        elif scenario == "CONTAMINATION_SPIKE":
            return {
                "cod_peak": random.uniform(120.0, 190.0),
                "bod_peak": random.uniform(15.0, 30.0),
                "oag_peak": random.uniform(8.0, 18.0),
            }
        return {}

    # ------------------------------------------------------------------ #
    #  Info                                                                #
    # ------------------------------------------------------------------ #

    def get_scenario_info(self) -> dict:
        """Returns metadata about the currently active scenario."""
        return {
            "scenario":    self.active_scenario,
            "tick":        self._step_count,
            "description": SCENARIO_REGISTRY.get(self.active_scenario, {}).get("description", ""),
            "targets":     SCENARIO_REGISTRY.get(self.active_scenario, {}).get("target_params", []),
        }

    def list_scenarios(self) -> list:
        return list(SCENARIO_REGISTRY.keys())
