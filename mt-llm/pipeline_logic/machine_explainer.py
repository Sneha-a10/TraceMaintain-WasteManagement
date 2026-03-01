import json
import datetime
import os
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Constants
MODEL_NAME = "google/flan-t5-small"
LOG_FILE = "interaction_logs.json"
input_file = "final_recommendation.json"

class MachineExplainer:
    def __init__(self, model_name=MODEL_NAME):
        print(f"Loading model: {model_name}...")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        except Exception as e:
            print(f"FAILED TO LOAD MODEL: {e}")
            raise e
        
        # Use GPU if available
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        print(f"Model loaded on {self.device}.")

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
        kb_path = os.path.join("knowledge_base", "knowledgebase.json")
        
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
            
        print(f"\n[INFO] Knowledge Base updated with new chunk: {new_id}")

    def generate_explanation(self, decision_trace):
        # Load original trace data for observations
        trace_path = os.path.join("knowledge_base", "post_decision_trace.json")
        try:
            with open(trace_path, 'r') as f:
                trace_data = json.load(f)
        except Exception:
            trace_data = decision_trace # fallback

        # Extract recommendations specifically from the final_recommendation.json structure
        recommendations = decision_trace.get("recommended_action", [])
        if isinstance(recommendations, list):
            rec_text = "\n".join(rec for rec in recommendations if isinstance(rec, str))
        else:
            rec_text = str(recommendations)

        # Humanize trace using the ACTUAL sensor trace, not the recommendation!
        humanized = self._humanize_decision_trace(trace_data.get("input_trace", trace_data))
        observations_text = "\n".join(humanized["observations"])

        print(f"\n[DEBUG] observations_text extracted for Explanation Prompt is:\n{observations_text}\n")

        # Short-circuit for NORMAL traces
        if trace_data.get("input_trace", trace_data).get("decision") == "NORMAL":
            return "System is operating within normal parameters. No anomalies detected.", ["Maintain normal monitoring schedule. No immediate action required."]

        prompt = f"""
Task: You are an explainability AI for a Smart City utility dashboard. 
The deterministic rule engine has fired the following decision trace. Summarize what happened in ONE short, clear, and grammatically correct sentence ("What happened").

Decision Trace:
{observations_text}

Explanation:
"""
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True).to(self.device)

        outputs = self.model.generate(
            **inputs,
            max_length=150,
            min_length=10,
            do_sample=True,
            temperature=0.1,  # Lower temp for more deterministic/focused output
            top_p=0.9,
            repetition_penalty=2.0, # High penalty for repetition
        )

        explanation = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

        # Step 2: Generate Concise Actions
        action_prompt = f"""Task: Extract the core mechanical or maintenance action from the text below and summarize it into ONE short, clear, actionable sentence. Ignore any document headers, fax numbers, phone numbers, or administrative jargon. If no clear mechanical action exists, output "Conduct standard field inspection and report findings."

Manual Text:
{rec_text}

Summary:"""
        action_inputs = self.tokenizer(action_prompt, return_tensors="pt", truncation=True).to(self.device)
        action_outputs = self.model.generate(
            **action_inputs,
            max_length=100,
            min_length=15,
            do_sample=True,
            temperature=0.2,
            top_p=0.85,
            repetition_penalty=2.0
        )
        actions_raw = self.tokenizer.decode(action_outputs[0], skip_special_tokens=True).strip()
        
        # Clean up the output into a list format for the UI
        action_list = [actions_raw] if actions_raw else ["Conduct a standard field inspection.", "Verify utility sensor telemetry."]

        return explanation, action_list

    def log_interaction(self, input_trace, output_explanation, user_feedback=None):
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "input_trace": input_trace,
            "output_explanation": output_explanation,
            "user_feedback": user_feedback
        }

        # Append to existing log file or create new one
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, 'r') as f:
                    logs = json.load(f)
                    if not isinstance(logs, list):
                        logs = []
            except (json.JSONDecodeError, ValueError):
                logs = []
        else:
            logs = []

        logs.append(log_entry)

        with open(LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=4)
        
        print(f"Interaction logged to {LOG_FILE}")

INPUT_FILE = "final_recommendation.json"

def load_last_input(file_path):
    """Reads the JSON file and returns the last entry if it's a list."""
    if not os.path.exists(file_path):
        print(f"Error: Input file '{file_path}' not found.")
        return None
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        if isinstance(data, list):
            if not data:
                print("Error: Input list is empty.")
                return None
            print(f"Loaded input file with {len(data)} entries. Processing the last one.")
            return data[-1]
        elif isinstance(data, dict):
            print("Input file contains a single entry.")
            return data
        else:
            print("Error: Input file format not supported (must be list or dict).")
            return None
            
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None

def main():
    action = os.environ.get("ACTION", "GENERATE")
    
    # Load Input from File
    decision_trace = load_last_input(INPUT_FILE)
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
    with open("ai_explanation.json", "w") as f:
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