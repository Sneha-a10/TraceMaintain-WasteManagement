from datetime import datetime

from rules.rules_config import RULES
from trace_engine.trace_context import start_trace, end_trace
from trace_engine.trace_step import trace_step
from trace_engine.trace_persistence import save_trace


class RuleEngine:
    def __init__(self):
        pass

    def _compare(self, value, comparison, threshold):
        if comparison == ">":
            return value > threshold
        elif comparison == ">=":
            return value >= threshold
        elif comparison == "<":
            return value < threshold
        elif comparison == "<=":
            return value <= threshold
        else:
            raise ValueError(f"Unsupported comparison operator: {comparison}")

    def _decision_from_confidence(self, confidence):
        if confidence >= 0.7:
            return "ALARM"
        elif confidence >= 0.4:
            return "WARNING"
        elif confidence >= 0.1:
            return "BORDERLINE"
        else:
            return "NORMAL"

    def _severity_from_confidence(self, confidence):
        if confidence >= 0.7:
            return "CRITICAL"
        elif confidence >= 0.4:
            return "HIGH"
        elif confidence >= 0.1:
            return "MEDIUM"
        else:
            return "LOW"

    def evaluate(self, record: dict):
        """
        record format (flat):
        {
          "asset_id": "STP_DEMO",
          "BOD_mg_L": ...,
          "COD_mg_L": ...,
          ...
        }
        """
        asset_id = record.get("asset_id", "STP_DEMO")
        
        # In this system, asset_id maps directly to the rule set
        rules = RULES.get(asset_id, [])
        if not rules:
            # Fallback to a generic set if asset_id not found directly
            rules = RULES.get("STP_DEMO", [])

        # ---- START TRACE ----
        start_trace(component_id=asset_id)

        confidence = 0.0
        reasoning_trace_strings = []

        # ---- RULE EVALUATION ----
        for rule in rules:
            feature_name = rule["feature"]
            feature_value = record.get(feature_name)

            # If feature missing, skip rule safely
            if feature_value is None:
                continue

            fired = self._compare(
                feature_value,
                rule["comparison"],
                rule["threshold"]
            )

            if fired:
                confidence += rule["confidence_delta"]
                confidence = min(confidence, 1.0)
                
                # Create human-readable trace string
                explanation = rule.get("explanation", f"{feature_name} exceeded threshold")
                trace_str = f"{explanation} (value={feature_value}, threshold={rule['threshold']})"
                reasoning_trace_strings.append(trace_str)

                # Keep the structured step for internal tracking if needed
                trace_step({
                    "rule": rule["rule"],
                    "feature": feature_name,
                    "feature_value": feature_value,
                    "threshold": rule["threshold"],
                    "comparison": rule["comparison"],
                    "rule_result": "FIRED",
                    "explanation": trace_str
                })

        # ---- FINAL DECISION ----
        decision = self._decision_from_confidence(confidence)
        severity = self._severity_from_confidence(confidence)

        expected_behavior = "NORMAL"
        observed_behavior = "NORMAL" if decision == "NORMAL" else "ANOMALOUS"

        trace = end_trace(
            decision=decision,
            severity=severity,
            confidence_score=round(confidence, 2),
            expected_behavior=expected_behavior,
            observed_behavior=observed_behavior
        )
        
        # Override reasoning_trace with our string list for the requested output format
        trace["reasoning_trace"] = reasoning_trace_strings

        path = save_trace(trace)
        return trace, path
