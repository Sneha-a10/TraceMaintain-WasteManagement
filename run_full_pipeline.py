import json
import os
import sys
import subprocess
import time

# Projects paths
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
TRACE_ENGINE_DIR = os.path.join(PROJECT_ROOT, "trace-engine")
MT_LLM_DIR = os.path.join(PROJECT_ROOT, "mt-llm")
DATA_DIR = os.path.join(PROJECT_ROOT, "data-n-sensor", "output")

def run_step(name, command, cwd):
    print(f"\n>>> Running Step: {name}")
    try:
        # Pass environment variables
        env = os.environ.copy()
        env["NON_INTERACTIVE"] = "1"
        subprocess.run(command, check=True, cwd=cwd, env=env, shell=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {name} failed: {e}")
        return False

def main():
    print("=== STARTING FULL WASTEWATER MONITORING PIPELINE ===\n")

    # 1. RUN RULE ENGINE (Detection)
    # We'll use the test script we created which already picks a BOD spike
    rule_engine_cmd = "python tests/test_wastewater_engine.py"
    if not run_step("Rule Engine Detection", rule_engine_cmd, TRACE_ENGINE_DIR):
        print("Pipeline aborted at Detection.")
        return

    # After detection, we need to find the latest trace
    trace_dir = os.path.join(TRACE_ENGINE_DIR, "traces")
    traces = [os.path.join(trace_dir, f) for f in os.listdir(trace_dir) if f.endswith(".json")]
    if not traces:
        print("[ERROR] No traces generated.")
        return
    latest_trace_path = max(traces, key=os.path.getmtime)
    
    with open(latest_trace_path, 'r') as f:
        trace_data = json.load(f)

    # 2. UPDATE KNOWLEDGE BASE INPUT
    # The MT-LLM pipeline expects its input in mt-llm/knowledge_base/post_decision_trace.json
    kb_input_path = os.path.join(MT_LLM_DIR, "knowledge_base", "post_decision_trace.json")
    with open(kb_input_path, 'w') as f:
        json.dump({"input_trace": trace_data}, f, indent=4)
    print(f">>> Prepared MT-LLM input at {os.path.basename(kb_input_path)}")

    # 3. RUN RAG WORKFLOW (Context Retrieval)
    rag_cmd = "python pipeline_logic/process_alert_workflow.py"
    if not run_step("RAG Context Retrieval", rag_cmd, MT_LLM_DIR):
        print("Pipeline aborted at RAG.")
        return

    # 4. RUN MACHINE EXPLAINER (LLM Explanation)
    explainer_cmd = "python pipeline_logic/machine_explainer.py"
    if not run_step("LLM Explanation Generation", explainer_cmd, MT_LLM_DIR):
        print("Pipeline aborted at Explanation.")
        return

    # 5. RUN ROUTING AGENT (Dispatch)
    routing_cmd = "python pipeline_logic/routing_agent.py"
    if not run_step("Routing Agent Dispatch", routing_cmd, MT_LLM_DIR):
        print("Pipeline aborted at Routing.")
        return

    # 6. CONSOLIDATE FINAL OUTPUT
    print("\n" + "="*50)
    print("FINAL CONSOLIDATED OUTPUT")
    print("="*50)

    # Load results from components
    expl_path = os.path.join(MT_LLM_DIR, "ai_explanation.json")
    dispatch_path = os.path.join(MT_LLM_DIR, "dispatch_plan.json")
    rec_path = os.path.join(MT_LLM_DIR, "final_recommendation.json")

    with open(expl_path, 'r') as f:
        expl_data = json.load(f)
    with open(dispatch_path, 'r') as f:
        dispatch_data = json.load(f)
    with open(rec_path, 'r') as f:
        rec_data = json.load(f)

    final_json = {
        "alert": trace_data.get("alert_id"),
        "reasoning_trace": trace_data.get("reasoning_trace"),
        "explanation": expl_data.get("explanation"),
        "regulatory_reference": rec_data.get("reference"),
        "action_plan": " ".join(expl_data.get("recommended_action", [])),
        "notified_role": dispatch_data.get("role")
    }

    print(json.dumps(final_json, indent=2))
    
    # Save final output
    with open("full_pipeline_output.json", "w") as f:
        json.dump(final_json, f, indent=2)
    print(f"\n>>> Final output saved to full_pipeline_output.json")

if __name__ == "__main__":
    main()
