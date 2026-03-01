import json
import sys
import os
import subprocess

# Add parent directory to path so we can import trace_engine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trace_engine.rule_engine import RuleEngine

def run_test():
    engine = RuleEngine()

    # Path to simulated readings
    readings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data-n-sensor/output/simulated_readings.json'))
    
    if not os.path.exists(readings_path):
        print(f">>> {readings_path} not found. Running simulation...")
        sim_script = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data-n-sensor/run_simulation.py'))
        sim_cwd = os.path.dirname(sim_script)
        subprocess.run([sys.executable, sim_script, "--mode", "scenario", "--scenario", "BOD_SPIKE", "--ticks", "50"], check=True, cwd=sim_cwd)
        if not os.path.exists(readings_path):
            print("Error: Simulation failed to generate readings.")
            return

    with open(readings_path, "r") as f:
        records = json.load(f)

    # Find a record with a BOD spike (to ensure we see a trace)
    target_record = None
    for r in records:
        if r.get("BOD_mg_L", 0) > 35:
            target_record = r
            break
    
    if not target_record:
        print("Warning: No BOD spike found in data. Using first record.")
        target_record = records[0]

    print(f"Evaluating record at tick {target_record.get('tick')}:")
    print(json.dumps(target_record, indent=2))

    trace, path = engine.evaluate(target_record)

    print("\n--- RESULTING TRACE ---")
    print(json.dumps(trace, indent=2))
    print(f"\nTrace saved at: {path}")

if __name__ == "__main__":
    run_test()
