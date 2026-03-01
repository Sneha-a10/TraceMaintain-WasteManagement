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
        # Extract fields
        component = decision_trace.get("component")
        decision = decision_trace.get("decision", "NORMAL")
        
        # Determine location
        target_loc = self._get_issue_location(component)
        
        # Lookup action from KB
        comp_data = self.kb.get(component)
        action_data = None
        if comp_data:
            action_data = comp_data.get(decision)
        
        if not action_data:
            action_data = self.kb.get("DEFAULT", {"team": "General_Ops", "action": "Inspect", "priority": "LOW"})
            
        distance_to_target = self._calculate_distance(self.depot_location, target_loc)
        
        # Generate route steps
        if action_data["team"] == "None":
            route_steps = []
        else:
            route_steps = [
                {"step": 1, "instruction": f"Team {action_data['team']} depart City Depot.", "coords": self.depot_location},
                {"step": 2, "instruction": f"Proceed to sector ({distance_to_target}km route).", "coords": target_loc},
                {"step": 3, "instruction": f"Execute orders: {action_data['action']}", "coords": target_loc}
            ]
            
        return {
            "component": component,
            "decision": decision,
            "assigned_team": action_data["team"],
            "priority": action_data["priority"],
            "recommended_action": action_data["action"],
            "route_steps": route_steps
        }

if __name__ == "__main__":
    # Called directly by the pipeline
    base_dir = os.path.dirname(os.path.dirname(__file__))
    input_file = os.path.join(base_dir, "knowledge_base", "post_decision_trace.json")
    output_file = os.path.join(base_dir, "dispatch_plan.json")
    
    agent = CityRoutingAgent()
    trace = {}
    
    # Read the trace
    if os.path.exists(input_file):
        with open(input_file, 'r') as f:
            data = json.load(f)
            # data has shape {"input_trace": {...}} from app.py
            trace = data.get("input_trace", {})
    else:
        print(f"Warning: {input_file} not found.")

    # Generate plan
    plan = agent.generate_dispatch_plan(trace)
    
    # Write to output
    with open(output_file, 'w') as f:
        json.dump(plan, f, indent=4)
        
    print(f"Dispatch plan generated to {output_file}")

