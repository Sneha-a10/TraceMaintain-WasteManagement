"""
End-to-end live simulation orchestrator (Python-only).

Flow:
1. Run data_generated.py
2. Run feature_extraction.py
3. Load extracted_features.json
4. Select 2 feature events per component
5. Run Trace Engine
6. Return results for UI
"""

import json
import os
import subprocess
from trace_engine.rule_engine import RuleEngine


# -------------------------------------------------
# PATH CONFIG
# -------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_SENSOR_DIR = os.path.join(BASE_DIR, "data-n-sensor")
RUN_SIM_SCRIPT = os.path.join(DATA_SENSOR_DIR, "run_simulation.py")
SIM_OUTPUT_JSON = os.path.join(DATA_SENSOR_DIR, "output", "simulated_readings.json")

def run_live_simulation():
    import sys
    # 1️⃣ Run raw data generation (Wastewater)
    # We run the BOD_SPIKE scenario for a dramatic demo
    subprocess.run(
        [sys.executable, RUN_SIM_SCRIPT, "--mode", "scenario", "--scenario", "BOD_SPIKE", "--ticks", "50"],
        check=True,
        cwd=DATA_SENSOR_DIR
    )

    # 2️⃣ Load simulated readings
    if not os.path.exists(SIM_OUTPUT_JSON):
        raise RuntimeError(f"simulated_readings.json not found at {SIM_OUTPUT_JSON}")

    with open(SIM_OUTPUT_JSON, "r") as f:
        readings = json.load(f)

    if not isinstance(readings, list):
        raise ValueError("simulated_readings.json must be a list")

    # 3️⃣ Select 3 representative events for the UI tabs
    # We pick them to show the progression: Normal -> Warning -> Danger
    selected_readings = []
    
    if len(readings) > 5:  selected_readings.append(readings[5])  # NORMAL (Baseline)
    if len(readings) > 35: selected_readings.append(readings[35]) # WARNING (Decaying BOD spike)
    if len(readings) > 10: selected_readings.append(readings[10]) # DANGER (Absolute peak of BOD spike)
    
    # If not enough readings, just take what we have
    if not selected_readings and readings:
        selected_readings = readings[:3]

    # 4️⃣ Run Rule Engine for each selected event
    engine = RuleEngine()
    results = []

    for r in selected_readings:
        # Prepare event format for rule engine - MUST MATCH rules_config.py exactly
        event = {
            "asset_id": r.get("asset_id", "STP_DEMO"),
            "timestamp": r.get("timestamp"),
            "pH": r.get("pH"),
            "BOD_mg_L": r.get("BOD_mg_L"),
            "COD_mg_L": r.get("COD_mg_L"),
            "TSS_mg_L": r.get("TSS_mg_L"),
            "temperature_C": r.get("temperature_C", 25.0)
        }
        
        trace, trace_path = engine.evaluate(event)
        results.append({
            "component": event["asset_id"],
            "timestamp": event["timestamp"],
            "features": {
                "pH": event["pH"],
                "BOD": event["BOD_mg_L"],
                "COD": event["COD_mg_L"],
                "TSS": event["TSS_mg_L"],
                "Temp": event["temperature_C"]
            },
            "trace": trace,
            "trace_path": trace_path
        })

    return results
