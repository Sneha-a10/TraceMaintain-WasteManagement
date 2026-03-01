import os
import subprocess
import sys
import time

# Get the directory of this script (mt-llm root)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_script(script_path):
    """Runs a python script specifically in the mt-llm directory context."""
    print(f"\n{'='*50}")
    print(f"Running {os.path.basename(script_path)}...")
    print(f"{'='*50}\n")
    
    # Use the current executing python which has the right dependencies
    python_exe = sys.executable

    try:
        # Run from the mt-llm folder so relative paths inside scripts work
        result = subprocess.run([python_exe, script_path], check=True, cwd=SCRIPT_DIR)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] {script_path} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"\n[ERROR] Script {script_path} not found.")
        return False

def main():
    # Set non-interactive mode
    os.environ["NON_INTERACTIVE"] = "1"

    # Step 1: Run the RAG Workflow to generate recommendations
    rag_script = os.path.join("pipeline_logic", "process_alert_workflow.py")
    if not run_script(rag_script):
        print("\n[STOP] Pipeline halted due to error in RAG step.")
        return

    # Check if output file was created (inside mt-llm folder)
    output_file = os.path.join(SCRIPT_DIR, "final_recommendation.json")
    if not os.path.exists(output_file):
        print(f"\n[ERROR] {output_file} was not generated.")
        print("[STOP] Pipeline halted.")
        return
        
    print(f"\n[SUCCESS] RAG step completed. Output found.")
    
    # Step 2: Run the Machine Explainer
    time.sleep(1) # Brief pause for readability
    
    explainer_script = os.path.join("pipeline_logic", "machine_explainer.py")
    if not run_script(explainer_script):
        print("\n[STOP] Pipeline halted due to error in Explainer step.")
        return

    # Step 3: Run the Routing Agent
    time.sleep(1)
    routing_script = os.path.join("pipeline_logic", "routing_agent.py")
    if not run_script(routing_script):
        print("\n[STOP] Pipeline halted due to error in Routing step.")
        return

    print(f"\n{'='*50}")
    print("Full Pipeline Completed Successfully")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()
