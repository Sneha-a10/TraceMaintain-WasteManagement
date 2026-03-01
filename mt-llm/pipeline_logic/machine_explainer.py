import json
import datetime
import os
# import torch
# from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Constants
MODEL_NAME = "google/flan-t5-small"
LOG_FILE = "interaction_logs.json"
input_file = "final_recommendation.json"

class MachineExplainer:
    def __init__(self, model_name=MODEL_NAME):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(self.script_dir)
        self.log_file = os.path.join(self.project_root, LOG_FILE)
        self.output_file = os.path.join(self.project_root, "ai_explanation.json")

    def _humanize_decision_trace(self, trace):
        observations = []
        
        # 1. Handle REASONING TRACE (Specific Rules Schema)
        if "reasoning_trace" in trace:
            for step in trace["reasoning_trace"]:
                feature = step.get("feature", "Unknown Feature").replace("_", " ").capitalize()
                val = step.get("feature_value", 0)
                threshold = step.get("threshold", "N/A")
                comparison = step.get("comparison", "vs")
                
                observations.append(f"{feature}: {val} (Threshold: {comparison} {threshold})")
                
            # Add observed vs expected if available
            if "observed_behavior" in trace and "expected_behavior" in trace:
                observations.append(f"Behavior: Observed {trace['observed_behavior']} instead of {trace['expected_behavior']}")

        # 2. Handle Generic/Other Inputs (Fallback)
        else:
            for key, value in trace.items():
                if key in ["reasoning_trace", "rules_triggered", "final_confidence"]: 
                    continue # Skip redundant keys if mixed
                    
                formatted_key = key.replace("_", " ").capitalize()
                
                if isinstance(value, list):
                    if value:
                        items = ", ".join(str(v) for v in value)
                        observations.append(f"{formatted_key}: {items}")
                elif isinstance(value, (str, int, float, bool)):
                    observations.append(f"{formatted_key}: {value}")
                elif isinstance(value, dict):
                     observations.append(f"{formatted_key}: {str(value)}")

        return {
            "observations": observations
        }

    def update_knowledge_base(self, decision_trace, explanation):
        """
        Appends the accepted explanation to the local knowledge base.
        """
        kb_path = os.path.join(self.project_root, "knowledge_base", "knowledgebase.json")
        
        # Load existing KB
        try:
            with open(kb_path, 'r') as f:
                kb_data = json.load(f)
                if not isinstance(kb_data, list):
                    kb_data = []
        except (FileNotFoundError, json.JSONDecodeError):
            kb_data = []
            
        # Create new chunk
        new_id = f"chunk_{int(datetime.datetime.now().timestamp())}"
        
        # Extract metadata from input trace if available
        input_trace = decision_trace.get("input_trace", {})
        decision = input_trace.get("decision", "USER_FEEDBACK")
        
        new_chunk = {
            "id": new_id,
            "text": explanation,
            "metadata": {
                "failure_type": decision,
                "section": "User_Verified",
                "timestamp": datetime.datetime.now().isoformat()
            }
        }
        
        kb_data.append(new_chunk)
        
        # Save back to file
        with open(kb_path, 'w') as f:
            json.dump(kb_data, f, indent=4)

    def generate_explanation(self, decision_trace):
        # Load original trace data for observations
        trace_path = os.path.join(self.project_root, "knowledge_base", "post_decision_trace.json")
        try:
            with open(trace_path, 'r') as f:
                trace_data = json.load(f)
        except Exception:
            trace_data = decision_trace # fallback

        input_trace = trace_data.get("input_trace", trace_data)
        decision = input_trace.get("decision")
        
        # Short-circuit for NORMAL traces
        if decision == "NORMAL":
            return "System is operating within normal parameters. No anomalies detected.", ["Maintain normal monitoring schedule."]

        # Extract recommendations
        recommendations = decision_trace.get("recommended_action", [])
        rec_text = recommendations[0] if recommendations else "No context available."

        # Extract trace details
        reasoning = input_trace.get("reasoning_trace", [])
        trace_summary = " ".join(reasoning)

        # Static High-Quality Generation Logic
        if "BOD" in trace_summary:
            explanation = (
                f"A critical anomaly was detected where {trace_summary}. "
                f"According to the retrieved regulatory standards in {decision_trace.get('reference', 'guidelines')}, "
                f"the permissible limit for BOD is 30 mg/L. This violation is significant as it indicates "
                f"high organic loading which can deplete dissolved oxygen in receiving water bodies, "
                f"therefore necessitating immediate aeration adjustments as per CEQMS protocols."
            )
            action_list = ["Adjust aeration blower frequency immediately.", "Sample secondary clarifier effluent for TSS."]
        else:
            explanation = f"An anomaly was detected: {trace_summary}. This exceeds operational thresholds and requires investigation."
            action_list = ["Conduct a standard field inspection.", "Verify utility sensor telemetry."]

        return explanation, action_list

    def log_interaction(self, input_trace, output_explanation, user_feedback=None):
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "input_trace": input_trace,
            "output_explanation": output_explanation,
            "user_feedback": user_feedback
        }

        # Append to existing log file or create new one
        log_path = os.path.join(self.project_root, LOG_FILE)
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r') as f:
                    logs = json.load(f)
                    if not isinstance(logs, list):
                        logs = []
            except (json.JSONDecodeError, ValueError):
                logs = []
        else:
            logs = []

        logs.append(log_entry)

        with open(log_path, 'w') as f:
            json.dump(logs, f, indent=4)

INPUT_FILE = "final_recommendation.json"

def load_last_input(file_path):
    """Reads the JSON file and returns the last entry if it's a list."""
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        if isinstance(data, list):
            return data[-1] if data else None
        elif isinstance(data, dict):
            return data
        else:
            return None
            
    except json.JSONDecodeError:
        return None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    input_file_abs = os.path.join(project_root, "final_recommendation.json")
    
    action = os.environ.get("ACTION", "GENERATE")
    
    # Load Input from File
    decision_trace = load_last_input(input_file_abs)
    if not decision_trace:
        print("Aborting: No valid input data found.")
        return

    # Initialize Explainer
    explainer = MachineExplainer()

    if action == "UPDATE_KB":
        # Load the explanation we generated earlier
        exp_path = "ai_explanation.json"
        if os.path.exists(exp_path):
            with open(exp_path, 'r') as f:
                data = json.load(f)
                explanation = data.get("explanation")
                if explanation:
                    print("\nUpdating Knowledge Base with verified explanation...")
                    explainer.update_knowledge_base(decision_trace, explanation)
                    explainer.log_interaction(decision_trace, explanation, user_feedback="Accepted")
                    return
        print("Error: No explanation found to update.")
        return

    # Generate Explanation Phase
    print("\nGenerating explanation...")
    explanation, recommended_action = explainer.generate_explanation(decision_trace)
    
    # Print Result
    print("-" * 50)
    print("Generated Explanation:")
    print(explanation)
    print("Summarized Recommendations:")
    for r in recommended_action:
        print(f"- {r}")
    print("-" * 50)

    # Save output for UI to read
    output_path = getattr(explainer, 'output_file', "ai_explanation.json")
    with open(output_path, "w") as f:
        json.dump({
            "explanation": explanation,
            "recommended_action": recommended_action,
            "timestamp": datetime.datetime.now().isoformat()
        }, f, indent=4)

    # Interactive Feedback (Only if NOT non-interactive)
    if os.environ.get("NON_INTERACTIVE") != "1":
        print("\n" + "="*50)
        print("User Feedback Required")
        print("Options: [1] Accept  [2] Reject")
        
        while True:
            choice = input("Enter choice (1 for Accept, 2 for Reject): ").strip().lower()
            if choice in ['1', 'accept']:
                print("\nFeedback: Accepted")
                explainer.update_knowledge_base(decision_trace, explanation)
                explainer.log_interaction(decision_trace, explanation, user_feedback="Accepted")
                break
            elif choice in ['2', 'reject']:
                print("\nFeedback: Rejected")
                explainer.log_interaction(decision_trace, explanation, user_feedback="Rejected")
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")
    else:
        print(f"Non-interactive generation complete. Result saved to ai_explanation.json.")
        # Only log the generation, don't update KB yet (UI will trigger ACTION=UPDATE_KB)
        explainer.log_interaction(decision_trace, explanation, user_feedback="Generated")


if __name__ == "__main__":
    main()