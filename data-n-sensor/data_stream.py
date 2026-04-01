# -*- coding: utf-8 -*-
"""
data_stream.py
==============
Smart Campus Wastewater Monitoring System
Data Streaming Simulation

Provides two streaming modes:
  1. generate_stream()      : Iterator-based — yields readings one by one.
  2. run_live_stream()      : Real-time mode — uses time.sleep(interval).
  3. generate_batch()       : Batch mode — returns N readings as a list.

Each reading is a CPCB OCEMS-compliant JSON packet produced by WastewaterAsset.

Scenario scheduling:
  A ScenarioSchedule can be passed to automatically switch scenarios
  at specified tick counts, simulating a realistic day of campus STP ops.
"""

import time
from typing import Iterator, List, Optional

from sensor_simulation import WastewaterAsset
from scenario_engine import ScenarioEngine
from output_formatter import format_reading, save_stream_to_file, generate_telemetry_summary, print_telemetry_summary


# ============================================================================
# SCENARIO SCHEDULE
# ============================================================================

class ScenarioSchedule:
    """
    Defines when to activate/deactivate scenarios during a simulation run.

    schedule : list of dicts, each with:
      - "tick"     : int   — simulation tick to fire at
      - "scenario" : str   — scenario name to activate ("NORMAL" to reset)

    Example
    -------
    schedule = [
        {"tick": 0,   "scenario": "NORMAL"},
        {"tick": 20,  "scenario": "COD_GRADUAL"},
        {"tick": 60,  "scenario": "NORMAL"},
        {"tick": 80,  "scenario": "BOD_SPIKE"},
        ...
    ]
    """

    def __init__(self, schedule: list):
        # Sort by tick to ensure correct ordering
        self.schedule = sorted(schedule, key=lambda x: x["tick"])
        self._index = 0

    def get_scenario_at_tick(self, tick: int) -> Optional[str]:
        """
        Returns the scenario name to activate at this tick, or None if no change.
        """
        while self._index < len(self.schedule):
            entry = self.schedule[self._index]
            if tick >= entry["tick"]:
                self._index += 1
                return entry["scenario"]
            else:
                break
        return None

    def reset(self):
        self._index = 0


# ============================================================================
# DEFAULT CAMPUS DAY SCHEDULE
# (models a realistic 8-hour shift of campus STP operation)
# ============================================================================

DEFAULT_CAMPUS_SCHEDULE = ScenarioSchedule([
    {"tick": 0,   "scenario": "NORMAL"},             # Startup
    {"tick": 3,   "scenario": "FLOW_SURGE"},          # Happens almost immediately
    {"tick": 8,   "scenario": "NORMAL"},              # Clears
    {"tick": 12,  "scenario": "COD_GRADUAL"},         # Struggling
    {"tick": 18,  "scenario": "NORMAL"},
    {"tick": 22,  "scenario": "CONTAMINATION_SPIKE"}, # Huge disaster
    {"tick": 28,  "scenario": "NORMAL"},              
    {"tick": 33,  "scenario": "pH_DRIFT"},            
    {"tick": 39,  "scenario": "NORMAL"},              
    {"tick": 44,  "scenario": "BOD_SPIKE"},        
    {"tick": 50,  "scenario": "NORMAL"},              
    {"tick": 55,  "scenario": "GRADUAL_DEGRADATION"}, 
    {"tick": 65,  "scenario": "NORMAL"},
])


# ============================================================================
# CORE STREAMING FUNCTIONS
# ============================================================================

def generate_stream(
    asset: WastewaterAsset,
    engine: ScenarioEngine,
    total_ticks: int,
    schedule: Optional[ScenarioSchedule] = None,
) -> Iterator[dict]:
    """
    Generator that yields one reading per tick.
    Does NOT sleep — pure data generation without wall-clock timing.

    Parameters
    ----------
    asset       : WastewaterAsset to simulate.
    engine      : ScenarioEngine attached to the asset.
    total_ticks : Number of simulation ticks to run.
    schedule    : Optional ScenarioSchedule for auto-scenario switching.

    Yields
    ------
    dict : CPCB OCEMS-compliant JSON reading.
    """
    if schedule:
        schedule.reset()

    for tick in range(total_ticks):
        # Apply schedule if provided
        if schedule:
            new_scenario = schedule.get_scenario_at_tick(tick)
            if new_scenario and new_scenario != engine.active_scenario:
                engine.activate(new_scenario)

        # Advance scenario state (modifies drifts)
        engine.step()

        # Advance sensor state (generates readings)
        asset.update_state()

        # Yield formatted reading
        reading = asset.to_json()
        reading["tick"] = tick
        yield reading


def generate_batch(
    asset: WastewaterAsset,
    engine: ScenarioEngine,
    total_ticks: int,
    schedule: Optional[ScenarioSchedule] = None,
) -> List[dict]:
    """
    Run the full simulation in batch mode and return all readings as a list.

    Parameters
    ----------
    asset, engine, total_ticks, schedule : same as generate_stream()

    Returns
    -------
    List[dict] : All simulation readings.
    """
    readings = []
    for reading in generate_stream(asset, engine, total_ticks, schedule):
        readings.append(reading)
    return readings


def run_live_stream(
    asset: WastewaterAsset,
    engine: ScenarioEngine,
    total_ticks: int,
    interval_seconds: float = 5.0,
    schedule: Optional[ScenarioSchedule] = None,
    verbose: bool = True,
    output_file: Optional[str] = None,
) -> List[dict]:
    """
    Real-time streaming mode. Sleeps `interval_seconds` between each tick.
    Simulates live OCEMS data feed.

    Parameters
    ----------
    asset, engine, total_ticks, schedule : same as generate_stream()
    interval_seconds : Wall-clock seconds between readings (default: 5).
    verbose          : If True, prints each reading to console.
    output_file      : If set, appends each reading as JSON to this file path.

    Returns
    -------
    List[dict] : All readings produced during the stream.
    """
    all_readings = []

    print(f"\n{'='*60}")
    print(f"  SMART CAMPUS WASTEWATER MONITORING — LIVE STREAM")
    print(f"  Asset: {asset.asset_id}")
    print(f"  Ticks: {total_ticks} | Interval: {interval_seconds}s")
    print(f"{'='*60}\n")

    for reading in generate_stream(asset, engine, total_ticks, schedule):
        all_readings.append(reading)

        if verbose:
            _print_reading(reading)

        if output_file:
            save_stream_to_file([reading], output_file, append=True)

        time.sleep(interval_seconds)

    print(f"\n{'='*60}")
    print(f"  Stream complete. {len(all_readings)} readings generated.")
    print(f"{'='*60}\n")

    return all_readings


# ============================================================================
# MULTI-ASSET STREAM
# ============================================================================

def generate_multi_asset_batch(
    assets_configs: list,
    total_ticks: int,
    use_default_schedule: bool = True,
) -> List[dict]:
    """
    Simulates multiple campus STP assets in parallel (logically).
    Each asset gets its own WastewaterAsset + ScenarioEngine.

    Parameters
    ----------
    assets_configs : list of dicts, each with:
                     {"asset_id": str, "sampling_interval": float}
    total_ticks    : Number of ticks per asset.
    use_default_schedule : Apply the DEFAULT_CAMPUS_SCHEDULE to each asset.

    Returns
    -------
    List[dict] : All readings from all assets, interleaved by tick.
    """
    all_readings = []

    for config in assets_configs:
        asset = WastewaterAsset(
            asset_id=config["asset_id"],
            sampling_interval=config.get("sampling_interval", 5.0),
        )
        engine = ScenarioEngine(asset)
        schedule = DEFAULT_CAMPUS_SCHEDULE if use_default_schedule else None

        readings = generate_batch(asset, engine, total_ticks, schedule)
        all_readings.extend(readings)

        print(f"[OK] Simulated {total_ticks} ticks for asset: {config['asset_id']}")

    return all_readings


# ============================================================================
# Console printer
# ============================================================================

def _print_reading(reading: dict) -> None:
    print(
        f"[Tick {reading.get('tick', '?'):>4}] "
        f"{reading['asset_id']} | "
        f"pH={reading['pH']:.2f}  "
        f"COD={reading['COD_mg_L']:.1f}  "
        f"BOD={reading['BOD_mg_L']:.1f}  "
        f"TSS={reading['TSS_mg_L']:.1f}  "
        f"Flow={reading['flow_rate_m3_hr']:.1f} m3/hr  "
        f"[{reading.get('scenario', 'NORMAL')}]"
    )
