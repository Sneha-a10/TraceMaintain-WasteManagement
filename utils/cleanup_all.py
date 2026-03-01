"""
Utility script to clean all generated artifacts and logs.
Provides a clean slate for the wastewater monitoring demo.
"""

import os
import shutil

# Project Root (Assumes script is in utils/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Paths to clean (Relative to PROJECT_ROOT)
PATHS_TO_CLEAN = [
    os.path.join("trace-engine", "traces"),
    os.path.join("mt-llm", "interaction_logs.json"),
    os.path.join("mt-llm", "ai_explanation.json"),
    os.path.join("mt-llm", "final_recommendation.json"),
    os.path.join("mt-llm", "dispatch_plan.json"),
    os.path.join("mt-llm", "knowledge_base", "post_decision_trace.json"),
    os.path.join("data-n-sensor", "output", "simulated_readings.json"),
    "full_pipeline_output.json"
]

def cleanup():
    print("=== STARTING PROJECT CLEANUP ===\n")
    deleted_count = 0

    for path in PATHS_TO_CLEAN:
        abs_path = os.path.join(PROJECT_ROOT, path)
        
        if not os.path.exists(abs_path):
            continue

        try:
            if os.path.isdir(abs_path):
                # Clean directory contents but keep the directory (standard for traces/)
                files = os.listdir(abs_path)
                for f in files:
                    f_path = os.path.join(abs_path, f)
                    if os.path.isfile(f_path):
                        os.remove(f_path)
                        deleted_count += 1
                print(f"✓ Cleaned directory: {path}")
            else:
                # Remove individual files
                os.remove(abs_path)
                deleted_count += 1
                print(f"✓ Removed file: {path}")
        except Exception as e:
            print(f"✗ Failed to clean {path}: {e}")

    print(f"\nCleanup complete. Removed {deleted_count} artifact(s).")

if __name__ == "__main__":
    cleanup()
