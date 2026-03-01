# -*- coding: utf-8 -*-
"""
output_formatter.py
===================
Smart Campus Wastewater Monitoring System
Output Formatting Module

Responsibilities:
  - CPCB OCEMS-ordered JSON output formatting
  - CSV export
  - File I/O helpers

NOTE: This module formats raw telemetry only.
      No regulatory limits, compliance status, or violation logic here.
      Threshold comparison belongs in the downstream reasoning module.
"""

import json
import csv
import os
from typing import List, Optional


# OCEMS standard field ordering (matches CPCB reporting format — telemetry fields only)
OCEMS_FIELDS = [
    "asset_id",
    "timestamp",
    "scenario",
    "flow_rate_m3_hr",
    "total_volume_m3",
    "pH",
    "BOD_mg_L",
    "COD_mg_L",
    "TSS_mg_L",
    "ammonical_N_mg_L",
    "oil_grease_mg_L",
    "temperature_C",
    "tick",
]


# ============================================================================
# FORMATTING
# ============================================================================

def format_reading(reading: dict, include_tick: bool = True) -> dict:
    """
    Returns a clean, CPCB OCEMS-ordered copy of a reading dict.
    Drops internal fields not needed in OCEMS output.

    Parameters
    ----------
    reading      : Raw reading dict from WastewaterAsset.to_json()
    include_tick : Whether to include the simulation tick number.

    Returns
    -------
    dict : Ordered, formatted reading.
    """
    formatted = {}
    for field in OCEMS_FIELDS:
        if field == "tick" and not include_tick:
            continue
        if field in reading:
            formatted[field] = reading[field]
    return formatted


def readings_to_json_string(readings: List[dict], indent: int = 2) -> str:
    """
    Serialise a list of readings to a JSON string.
    """
    formatted = [format_reading(r) for r in readings]
    return json.dumps(formatted, indent=indent, default=str)


# ============================================================================
# FILE I/O
# ============================================================================

def save_stream_to_file(
    readings: List[dict],
    filepath: str,
    append: bool = False,
    indent: int = 2,
) -> str:
    """
    Save a list of readings to a JSON file.

    Parameters
    ----------
    readings  : List of reading dicts.
    filepath  : Output file path.
    append    : If True, load existing file and extend; else overwrite.
    indent    : JSON indentation.

    Returns
    -------
    str : The filepath written to.
    """
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

    formatted = [format_reading(r) for r in readings]

    if append and os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                existing = json.load(f)
                if isinstance(existing, list):
                    formatted = existing + formatted
        except (json.JSONDecodeError, ValueError):
            pass  # Overwrite if corrupted

    with open(filepath, "w") as f:
        json.dump(formatted, f, indent=indent, default=str)

    return filepath


def save_to_csv(readings: List[dict], filepath: str) -> str:
    """
    Export readings to a flat CSV file.
    Violations list is serialised as a pipe-separated string.

    Parameters
    ----------
    readings : List of reading dicts.
    filepath : Output CSV file path.

    Returns
    -------
    str : The filepath written to.
    """
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

    if not readings:
        return filepath

    rows = []
    for r in readings:
        row = format_reading(r, include_tick=True)
        rows.append(row)

    fieldnames = [f for f in OCEMS_FIELDS if f in rows[0]]

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return filepath


# ============================================================================
# TELEMETRY SUMMARY  (no compliance — descriptive stats only)
# ============================================================================

def generate_telemetry_summary(readings: List[dict]) -> dict:
    """
    Computes descriptive statistics over a list of raw telemetry readings.
    Does NOT compare against any regulatory limit.

    Returns
    -------
    dict with keys:
      total_readings  : int
      scenarios_seen  : list of unique scenario labels
      max_values      : dict — parameter → observed maximum
      min_values      : dict — parameter → observed minimum
      avg_values      : dict — parameter → observed mean
    """
    total = len(readings)
    if total == 0:
        return {"error": "No readings to summarise."}

    scenarios = set()
    param_values: dict = {
        "pH": [], "BOD_mg_L": [], "COD_mg_L": [], "TSS_mg_L": [],
        "ammonical_N_mg_L": [], "oil_grease_mg_L": [],
        "flow_rate_m3_hr": [], "temperature_C": [],
    }

    for r in readings:
        scenarios.add(r.get("scenario", "UNKNOWN"))
        for param in param_values:
            if param in r:
                param_values[param].append(r[param])

    return {
        "total_readings": total,
        "scenarios_seen": sorted(list(scenarios)),
        "max_values":     {p: round(max(v), 3) if v else None for p, v in param_values.items()},
        "min_values":     {p: round(min(v), 3) if v else None for p, v in param_values.items()},
        "avg_values":     {p: round(sum(v) / len(v), 3) if v else None for p, v in param_values.items()},
    }


def print_telemetry_summary(summary: dict) -> None:
    """Pretty-prints a raw telemetry summary to the console."""
    print("\n" + "="*60)
    print("  CPCB OCEMS — RAW TELEMETRY SUMMARY")
    print("="*60)
    print(f"  Total Readings      : {summary['total_readings']}")
    print(f"  Scenarios Simulated : {', '.join(summary['scenarios_seen'])}")
    print("\n  Observed Ranges (min / avg / max):")
    for p in ["pH", "BOD_mg_L", "COD_mg_L", "TSS_mg_L",
              "ammonical_N_mg_L", "oil_grease_mg_L", "flow_rate_m3_hr", "temperature_C"]:
        mn = summary["min_values"].get(p, "N/A")
        av = summary["avg_values"].get(p, "N/A")
        mx = summary["max_values"].get(p, "N/A")
        print(f"    {p:<25} : min={mn}  avg={av}  max={mx}")
    print("="*60 + "\n")
