import uuid
from datetime import datetime

# ---- TRACE CREATION ----

def create_trace(component_id: str):
    return {
        "alert_id": f"alert_{uuid.uuid4().hex[:8]}",
        "component_id": component_id,
        "timestamp": datetime.utcnow().isoformat(),

        "decision": None,
        "severity": None,
        "confidence_score": 0.0,

        "rules_triggered": [],
        "reasoning_trace": [],  # List of human-readable strings

        "expected_behavior": None,
        "observed_behavior": None,
        "expectation_mismatch": None
    }


# ---- TRACE MUTATION ----

def add_trace_step(trace: dict, step_data: dict):
    trace["reasoning_trace"].append(step_data)

    rule_name = step_data.get("rule")
    if rule_name and rule_name not in trace["rules_triggered"]:
        trace["rules_triggered"].append(rule_name)


def finalize_trace(
    trace: dict,
    decision: str,
    severity: str,
    confidence_score: float,
    expected_behavior: str,
    observed_behavior: str
):
    trace["decision"] = decision
    trace["severity"] = severity
    trace["confidence_score"] = confidence_score
    trace["expected_behavior"] = expected_behavior
    trace["observed_behavior"] = observed_behavior
    trace["expectation_mismatch"] = (expected_behavior != observed_behavior)


# ---- TRACE CONTEXT MANAGER ----

_active_trace = None


def start_trace(component_id: str):
    global _active_trace
    _active_trace = create_trace(component_id)
    return _active_trace


def get_active_trace():
    return _active_trace


def end_trace(
    decision: str,
    severity: str,
    confidence_score: float,
    expected_behavior: str,
    observed_behavior: str
):
    global _active_trace

    if _active_trace is None:
        raise RuntimeError("No active trace to finalize")

    finalize_trace(
        _active_trace,
        decision,
        severity,
        confidence_score,
        expected_behavior,
        observed_behavior
    )

    completed_trace = _active_trace
    _active_trace = None
    return completed_trace
