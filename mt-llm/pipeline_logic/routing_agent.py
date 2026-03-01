import json
import os
import math

class CityRoutingAgent:
    def __init__(self, kb_path=None):
        if kb_path is None:
            # Default path relative to this script
            kb_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base", "city_actions_kb.json")
        try:
            with open(kb_path, 'r') as f:
                self.kb = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load KB at {kb_path} ({e}). Using empty KB.")
            self.kb = {}
        
        self.depot_location = (40.7128, -74.0060) # City Base Station (e.g., NY coordinates)

    def _get_issue_location(self, component):
        # Deterministic mock locations based on component type
        locations = {
            "PUMP": (40.7138, -74.0160),      # Water facility down the road
            "CONVEYOR": (40.7228, -73.9960),  # Material recovery facility
            "COMPRESSOR": (40.7028, -74.0200) # Underground pneumatic hub
        }
        return locations.get(component, (40.7100, -74.0000))

    def _calculate_distance(self, loc1, loc2):
        # Simple Euclidean distance scaled to rough km string
        dist = math.sqrt((loc1[0] - loc2[0])**2 + (loc1[1] - loc2[1])**2)
        # 1 degree approx 111km
        return round(dist * 111.0, 2)

    def generate_dispatch_plan(self, decision_trace: dict) -> dict:
        """
        Deterministic routing based on severity:
        HIGH or CRITICAL -> Environmental Officer
        MEDIUM -> Floor Engineer
        """
        severity = decision_trace.get("severity", "LOW")
        
        # Determinstic logic
        if severity in ["HIGH", "CRITICAL"]:
            role = "Environmental Officer"
            urgency = "CRITICAL"
            action = "Immediate on-site audit and discharge stoppage."
        elif severity == "MEDIUM":
            role = "Floor Engineer"
            urgency = "HIGH"
            action = "Check aeration tanks and adjust blower frequency."
        else:
            role = "Maintenance Technician"
            urgency = "NORMAL"
            action = "Conduct standard equipment check."

        return {
            "role": role,
            "urgency": urgency,
            "recommended_action": action
        }

if __name__ == "__main__":
    # Called directly by the pipeline
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # We use final_recommendation.json (output of explainer) or post_decision_trace.json
    # The user request asks for severity mapping which is in the trace.
    input_file = os.path.join(project_root, "knowledge_base", "post_decision_trace.json")
    output_file = os.path.join(project_root, "dispatch_plan.json")
    
    agent = CityRoutingAgent()
    trace = {}
    
    # Read the trace
    if os.path.exists(input_file):
        with open(input_file, 'r') as f:
            data = json.load(f)
            # Handle standard nested structure
            trace = data.get("input_trace", data)
    else:
        print(f"Warning: {input_file} not found.")

    # Generate plan
    plan = agent.generate_dispatch_plan(trace)
    
    # Write to output
    with open(output_file, 'w') as f:
        json.dump(plan, f, indent=4)
        
    print(f"Dispatch plan generated to {output_file}")

