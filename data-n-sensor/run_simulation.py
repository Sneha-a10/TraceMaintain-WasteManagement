# -*- coding: utf-8 -*-
"""
run_simulation.py
=================
Smart Campus Wastewater Monitoring System
Entry Point / Demo Runner

Demonstrates the full sensor simulation pipeline:
  1. Creates campus STP assets
  2. Attaches a ScenarioEngine per asset
  3. Runs a batch simulation using a day schedule
  4. Saves JSON + CSV output
  5. Prints a violation report

Usage:
    python run_simulation.py
    python run_simulation.py --mode live     # Real-time (sleeps 5s/tick)
    python run_simulation.py --ticks 100     # Custom tick count
    python run_simulation.py --scenario BOD_SPIKE  # Single scenario demo

Outputs (saved in data-n-sensor/output/):
    simulated_readings.json   — all readings in CPCB OCEMS format
    simulated_readings.csv    — flat CSV version
    violation_report.json     — summary statistics
"""

import json
import os
import sys
import argparse
import time
import random
import threading

from sensor_simulation import WastewaterAsset
from scenario_engine import ScenarioEngine, SCENARIO_REGISTRY
from data_stream import (
    generate_batch,
    run_live_stream,
    generate_multi_asset_batch,
    DEFAULT_CAMPUS_SCHEDULE,
    ScenarioSchedule,
)
from output_formatter import (
    save_stream_to_file,
    save_to_csv,
    generate_telemetry_summary,
    print_telemetry_summary,
    format_reading,
)
from network_client import IoTNetworkClient


# ============================================================================
# OUTPUT DIRECTORY
# ============================================================================
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


# ============================================================================
# CAMPUS ASSET CONFIGS
# ============================================================================
CAMPUS_ASSETS = [
    {"asset_id": "STP_HOSTEL_A",   "sampling_interval": 5.0},
    {"asset_id": "STP_HOSTEL_B",   "sampling_interval": 5.0},
    {"asset_id": "STP_CANTEEN",    "sampling_interval": 5.0},
    {"asset_id": "STP_LAB_BLOCK",  "sampling_interval": 5.0},
]


# ============================================================================
# MODES
# ============================================================================

def run_batch_mode(ticks: int) -> None:
    """
    Runs all campus STP assets in batch (no sleep), saves output.
    """
    print(f"\n{'='*60}")
    print(f"  MODE: BATCH SIMULATION")
    print(f"  Ticks: {ticks} per asset | Assets: {len(CAMPUS_ASSETS)}")
    print(f"{'='*60}\n")

    all_readings = generate_multi_asset_batch(
        assets_configs=CAMPUS_ASSETS,
        total_ticks=ticks,
        use_default_schedule=True,
    )

    # Save JSON
    json_path = os.path.join(OUTPUT_DIR, "simulated_readings.json")
    save_stream_to_file(all_readings, json_path)
    print(f"\n✅ JSON saved → {json_path}  ({len(all_readings)} readings)")

    # Save CSV
    csv_path = os.path.join(OUTPUT_DIR, "simulated_readings.csv")
    save_to_csv(all_readings, csv_path)
    print(f"✅ CSV  saved → {csv_path}")

    # Telemetry Summary
    summary = generate_telemetry_summary(all_readings)
    report_path = os.path.join(OUTPUT_DIR, "telemetry_summary.json")
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\u2705 Summary saved \u2192 {report_path}")

    print_telemetry_summary(summary)


def run_live_mode(ticks: int, interval: float = 5.0) -> None:
    """
    Runs a single asset in real-time mode (sleeps between ticks).
    """
    asset  = WastewaterAsset("STP_HOSTEL_A", sampling_interval=interval)
    engine = ScenarioEngine(asset)

    readings = run_live_stream(
        asset=asset,
        engine=engine,
        total_ticks=ticks,
        interval_seconds=interval,
        schedule=DEFAULT_CAMPUS_SCHEDULE,
        verbose=True,
        output_file=os.path.join(OUTPUT_DIR, "live_stream.json"),
    )

    report = generate_telemetry_summary(readings)
    print_telemetry_summary(report)


def _asset_stream_worker(asset_config: dict, endpoint: str, interval: float, stop_event: threading.Event) -> None:
    """Thread worker: continually polls a single asset and streams to API."""
    asset_id = asset_config["asset_id"]
    client = IoTNetworkClient(endpoint=endpoint)
    
    asset = WastewaterAsset(asset_id, sampling_interval=interval)
    engine = ScenarioEngine(asset)
    schedule = DEFAULT_CAMPUS_SCHEDULE
    
    tick = 0
    print(f"[WORKER START] Device {asset_id} streaming to {endpoint} every {interval}s")
    
    while not stop_event.is_set():
        active_scenario_name = schedule.get_scenario_at_tick(tick)
        if active_scenario_name and asset.active_scenario != active_scenario_name:
            engine.activate(active_scenario_name)
        engine.step()
        asset.update_state()
        
        raw = asset.to_json()
        raw["tick"] = tick
        reading = format_reading(raw, include_tick=True)
        
        jitter = random.uniform(0.0, 1.5)
        time.sleep(jitter)
        
        success = client.send_telemetry(reading)
        
        if success:
            print(f"[Tick {tick:>4}] [POST OK] {asset_id} | pH={reading['pH']:.2f} Flow={reading['flow_rate_m3_hr']:.1f} m\u00b3/hr")
        
        tick += 1
        remaining = max(0.1, interval - jitter)
        stop_event.wait(remaining)


def run_stream_mode(endpoint: str, interval: float = 5.0) -> None:
    """
    Runs all campus assets independently in a multithreaded stream.
    Mimics real distributed IoT devices making POST requests.
    """
    print(f"\n{'='*60}")
    print(f"  MODE: NETWORK STREAMING")
    print(f"  Endpoint : {endpoint}")
    print(f"  Interval : {interval}s (with network jitter)")
    print(f"  Devices  : {len(CAMPUS_ASSETS)}")
    print(f"  Press Ctrl+C to stop.")
    print(f"{'='*60}\n")
    
    stop_event = threading.Event()
    threads = []
    
    for config in CAMPUS_ASSETS:
        t = threading.Thread(
            target=_asset_stream_worker,
            args=(config, endpoint, interval, stop_event),
            daemon=True
        )
        t.start()
        threads.append(t)
        
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[STOPPING] Ctrl+C received. Shutting down device streams...")
        stop_event.set()
        for t in threads:
            t.join(timeout=2.0)
        print("[STOPPED] All streams terminated.")


def run_single_scenario(scenario_name: str, ticks: int = 80) -> None:
    """
    Runs one specific scenario isolation demo (single asset, no schedule).
    """
    if scenario_name not in SCENARIO_REGISTRY:
        print(f"❌ Unknown scenario: '{scenario_name}'")
        print(f"   Available: {list(SCENARIO_REGISTRY.keys())}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  MODE: SCENARIO ISOLATION - {scenario_name}")
    print(f"  {SCENARIO_REGISTRY[scenario_name]['description']}")
    print(f"{'='*60}\n")

    asset  = WastewaterAsset("STP_DEMO", sampling_interval=5.0)
    engine = ScenarioEngine(asset)

    # Fixed schedule: start NORMAL for 10 ticks, then trigger scenario
    schedule = ScenarioSchedule([
        {"tick": 0,  "scenario": "NORMAL"},
        {"tick": 10, "scenario": scenario_name},
    ])

    readings = generate_batch(asset, engine, total_ticks=ticks, schedule=schedule)

    # Print first/last few ticks
    print(f"\nFirst 5 readings:")
    for r in readings[:5]:
        print(f"  Tick {r['tick']:>3} | pH={r['pH']}  COD={r['COD_mg_L']}  BOD={r['BOD_mg_L']}  TSS={r['TSS_mg_L']}")

    print(f"\nLast 5 readings:")
    for r in readings[-5:]:
        print(f"  Tick {r['tick']:>3} | pH={r['pH']}  COD={r['COD_mg_L']}  BOD={r['BOD_mg_L']}  TSS={r['TSS_mg_L']}")

    # Save output
    out_path = os.path.join(OUTPUT_DIR, "simulated_readings.json")
    save_stream_to_file(readings, out_path)
    print(f"\n[OK] Scenario output -> {out_path}")


# ============================================================================
# CLI ARGUMENT PARSING
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Smart Campus Wastewater Monitoring — Sensor Simulation"
    )
    parser.add_argument(
        "--mode",
        choices=["batch", "live", "scenario", "stream"],
        default="batch",
        help="Simulation mode (default: batch)",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="http://localhost:8000/ingest",
        help="API Endpoint for --mode stream (default: http://localhost:8000/ingest)",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=360,
        help="Number of simulation ticks (default: 360)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Seconds per tick for live mode (default: 5.0)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Scenario name for --mode scenario",
    )
    return parser.parse_args()


# ============================================================================
# MAIN
# ============================================================================

def main():
    args = parse_args()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.mode == "batch":
        run_batch_mode(ticks=args.ticks)

    elif args.mode == "live":
        run_live_mode(ticks=args.ticks, interval=args.interval)

    elif args.mode == "stream":
        run_stream_mode(endpoint=args.endpoint, interval=args.interval)

    elif args.mode == "scenario":
        scenario = args.scenario
        if not scenario:
            print("[FAIL] Please specify --scenario <NAME>")
            print(f"   Available: {list(SCENARIO_REGISTRY.keys())}")
            sys.exit(1)
        run_single_scenario(scenario_name=scenario, ticks=args.ticks)


if __name__ == "__main__":
    main()
