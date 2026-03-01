import streamlit as st
import sys
import os
import subprocess
import json
import datetime

# -------------------------------------------------
# Path Configuration
# -------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# The integration module is inside the trace-engine folder
sys.path.append(os.path.join(PROJECT_ROOT, "trace-engine"))

from integration.run_live_simulation import run_live_simulation

# -------------------------------------------------
# Streamlit Page Config
# -------------------------------------------------
st.set_page_config(
    page_title="IOT-Trace: Wastewater Monitoring Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# Custom CSS for Premium Look
# -------------------------------------------------
st.markdown("""
<style>
    /* Global Reset */
    .stApp {
        background-color: #0d1117;
        font-family: 'Inter', 'Segoe UI', Roboto, sans-serif;
        color: #c9d1d9;
    }
    
    /* Header Section */
    .header-container {
        background: linear-gradient(90deg, #161b22 0%, #0d1117 100%);
        padding: 2rem;
        border-bottom: 1px solid #30363d;
        margin-bottom: 2rem;
        border-radius: 8px;
    }
    .asset-id { font-size: 0.9rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }
    .status-text { font-size: 2.5rem; font-weight: 800; margin: 0.5rem 0; }
    .conf-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        background: rgba(31, 111, 235, 0.2);
        color: #58a6ff;
        border-radius: 20px;
        font-weight: 600;
        font-size: 1rem;
    }
    
    /* Panels */
    .glass-panel {
        background: rgba(22, 27, 34, 0.7);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1.5rem;
        height: 100%;
        margin-bottom: 1rem;
    }
    .panel-title {
        font-size: 0.85rem;
        font-weight: 700;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 1.25rem;
        display: flex;
        align-items: center;
    }
    .panel-title i { margin-right: 8px; font-size: 1.1rem; }
    
    /* Metrics */
    .metric-val { font-size: 2rem; font-weight: 700; color: #f0f6fc; }
    .metric-label { font-size: 0.8rem; color: #8b949e; }
    
    /* Reasoning Bullets */
    .reasoning-list { list-style: none; padding: 0; margin: 0; }
    .reasoning-item {
        padding: 0.75rem;
        border-left: 3px solid #f85149;
        background: rgba(248, 81, 73, 0.05);
        margin-bottom: 0.75rem;
        border-radius: 0 4px 4px 0;
        font-size: 0.95rem;
    }
    .item-normal { border-left-color: #3fb950; background: rgba(63, 185, 80, 0.05); }
    
    /* Narrative Box */
    .narrative-box {
        background: rgba(210, 168, 255, 0.05);
        border-left: 4px solid #d2a8ff;
        padding: 1.25rem;
        font-style: italic;
        line-height: 1.6;
        color: #e6edf3;
        font-size: 1.05rem;
        border-radius: 0 8px 8px 0;
    }
    
    /* Regulation Box */
    .reg-box {
        background: rgba(31, 111, 235, 0.05);
        border: 1px dashed #30363d;
        padding: 1rem;
        border-radius: 8px;
        color: #c9d1d9;
        font-size: 0.9rem;
    }
    
    /* Responsibility Footer */
    .resp-footer {
        background: #161b22;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 1px solid #30363d;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Pipeline Orchestration
# -------------------------------------------------
def export_trace_to_llm(trace, component="UNKNOWN"):
    # PROJECT_ROOT is Waste_management root. mt-llm is inside it.
    llm_input_path = os.path.join(PROJECT_ROOT, "mt-llm", "knowledge_base", "post_decision_trace.json")
    try:
        os.makedirs(os.path.dirname(llm_input_path), exist_ok=True)
        data = {"input_trace": trace}
        with open(llm_input_path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        st.error(f"Failed to export trace: {e}")

def run_ai_pipeline():
    env = os.environ.copy()
    env["NON_INTERACTIVE"] = "1"
    python_exe = sys.executable
    # PROJECT_ROOT is Waste_management root. mt-llm is inside it.
    base_path = os.path.join(PROJECT_ROOT, "mt-llm")
    
    # We run the consolidated script created earlier if available, 
    # but here we follow the app.py pattern for granular steps
    try:
        scripts = [
            os.path.join(base_path, "pipeline_logic", "process_alert_workflow.py"),
            os.path.join(base_path, "pipeline_logic", "machine_explainer.py"),
            os.path.join(base_path, "pipeline_logic", "routing_agent.py")
        ]
        for script in scripts:
            subprocess.run([python_exe, script], cwd=base_path, env=env, check=True, capture_output=True)
        
        # Load final results
        rec_path = os.path.join(base_path, "final_recommendation.json")
        exp_path = os.path.join(base_path, "ai_explanation.json")
        route_path = os.path.join(base_path, "dispatch_plan.json")
        
        with open(rec_path, 'r') as f: recs = json.load(f)
        with open(exp_path, 'r') as f: expl = json.load(f)
        with open(route_path, 'r') as f: plan = json.load(f)
            
        return {**recs, **expl, "dispatch_plan": plan}
    except Exception as e:
        return {"error": str(e)}

# -------------------------------------------------
# State Management
# -------------------------------------------------
if "simulation_results" not in st.session_state:
    st.session_state.simulation_results = []
if "active_idx" not in st.session_state:
    st.session_state.active_idx = 0
if "cache" not in st.session_state:
    st.session_state.cache = {}

# -------------------------------------------------
# Sidebar Controls
# -------------------------------------------------
with st.sidebar:
    st.title("⚙️ Controls")
    if st.button("🚀 Run Live Simulation", type="primary", use_container_width=True):
        with st.status("Generating data...", expanded=False):
            st.session_state.simulation_results = run_live_simulation()
            if st.session_state.simulation_results:
                export_trace_to_llm(st.session_state.simulation_results[0]["trace"])
        st.session_state.active_idx = 0
        st.session_state.cache = {}
        st.rerun()

    if st.session_state.simulation_results:
        st.markdown("---")
        st.markdown("### 📡 Select Event")
        for i in range(len(st.session_state.simulation_results)):
            label = f"Event {i+1} : {st.session_state.simulation_results[i]['trace']['decision']}"
            if st.button(label, use_container_width=True, key=f"btn_{i}", 
                         type="primary" if i == st.session_state.active_idx else "secondary"):
                st.session_state.active_idx = i
                export_trace_to_llm(st.session_state.simulation_results[i]["trace"])
                st.rerun()

# -------------------------------------------------
# Main Dashboard UI
# -------------------------------------------------
# Auto-run simulation on first load if no results exist
if not st.session_state.simulation_results:
    with st.status("🚀 Initializing Wastewater Monitoring Engine...", expanded=True):
        st.write("Generating live sensor simulation (BOD Spike Scenario)...")
        st.session_state.simulation_results = run_live_simulation()
        if st.session_state.simulation_results:
            export_trace_to_llm(st.session_state.simulation_results[0]["trace"])
            st.write("✅ Ready! Loading dashboard...")
    st.rerun()

active_data = st.session_state.simulation_results[st.session_state.active_idx]
trace = active_data["trace"]
features = active_data["features"]

# 1️⃣ SYSTEM STATUS HEADER
status_map = {
    "ALARM": {"color": "#f85149", "label": "🚨 DANGER - EXTREME VIOLATION"},
    "WARNING": {"color": "#d29922", "label": "⚠️ WARNING - MODERATE SPIKE"},
    "NORMAL": {"color": "#3fb950", "label": "✅ SYSTEM NORMAL"},
}
config = status_map.get(trace["decision"], status_map["NORMAL"])

st.markdown(f"""
<div class="header-container">
    <div class="asset-id">Asset ID: {active_data['component']} • {active_data['timestamp']}</div>
    <div class="status-text" style="color: {config['color']};">{config['label']}</div>
    <div style="display: flex; gap: 1rem; align-items: center;">
        <div class="conf-badge">Confidence: {int(trace['confidence_score']*100)}%</div>
        <div style="color: #8b949e;">Severity: <span style="color: {config['color']}; font-weight: bold;">{trace['severity']}</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# Run AI Pipeline if needed
if st.session_state.active_idx not in st.session_state.cache:
    with st.spinner("🧠 AI interpreting trace..."):
        st.session_state.cache[st.session_state.active_idx] = run_ai_pipeline()
    st.rerun()

ai_results = st.session_state.cache[st.session_state.active_idx]

# Layout Grid
col1, col2 = st.columns([1, 1.5], gap="large")

with col1:
    # 2️⃣ LIVE SENSOR READINGS
    st.markdown("""<div class="panel-title">📡 Live Sensor Readings</div>""", unsafe_allow_html=True)
    m1, m2 = st.columns(2)
    m3, m4 = st.columns(2)
    
    with m1: st.metric("pH Level", f"{features['pH']:.2f}")
    with m2: st.metric("BOD (mg/L)", f"{features['BOD']:.1f}", delta=f"{features['BOD']-30:.1f}" if features['BOD']>30 else None, delta_color="inverse")
    with m3: st.metric("COD (mg/L)", f"{features['COD']:.1f}")
    with m4: st.metric("Temp (°C)", f"{features['Temp']:.1f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # 3️⃣ DECISION TRACE (CORE DIFFERENTIATOR)
    st.markdown("""<div class="panel-title">🔗 Decision Reasoning (Trace)</div>""", unsafe_allow_html=True)
    reasoning = trace.get("reasoning_trace", [])
    if reasoning:
        html = '<div class="reasoning-list">'
        for item in reasoning:
            html += f'<div class="reasoning-item">{item}</div>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown('<div class="reasoning-item item-normal">All sensor values within regulatory compliance limits.</div>', unsafe_allow_html=True)

with col2:
    # 5️⃣ LLM EXPLANATION
    st.markdown("""<div class="panel-title">🤖 Expert Interpretation</div>""", unsafe_allow_html=True)
    explanation = ai_results.get("explanation", "Generating...")
    st.markdown(f'<div class="narrative-box">{explanation}</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # 4️⃣ REGULATORY CONTEXT
    st.markdown("""<div class="panel-title">📜 Regulatory Compliance Context</div>""", unsafe_allow_html=True)
    ref = ai_results.get("reference", "Internal Guidelines")
    actions = ai_results.get("recommended_action", ["No specific regulatory notes found."])
    # Extract the main rule snippet if it's the first rec (common in our RAG stub)
    reg_text = actions[0] if actions else "Compliance standard: 30 mg/L BOD limit."
    st.markdown(f"""
    <div class="reg-box">
        <strong>Reference:</strong> {ref}<br><br>
        {reg_text}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 6️⃣ RECOMMENDED ACTION PLAN
    st.markdown("""<div class="panel-title">🛠️ Recommended Action Plan</div>""", unsafe_allow_html=True)
    # If the first rec was the reg snippet, use others for actions
    plan_actions = actions[1:] if len(actions) > 1 else actions
    if not plan_actions or plan_actions == [reg_text]:
        plan_actions = ["Continue regular monitoring.", "Record reading in logbook."]
        
    for act in plan_actions:
        st.markdown(f"- {act}")

# 7️⃣ ROUTING / RESPONSIBILITY SECTION
st.markdown("<br>", unsafe_allow_html=True)
plan = ai_results.get("dispatch_plan", {})
role = plan.get("role", "Operations Team")
urgency = plan.get("urgency", "Normal")

st.markdown(f"""
<div class="resp-footer">
    <div style="display: flex; align-items: center; gap: 1rem;">
        <span style="font-size: 1.5rem;">📬</span>
        <div>
            <div style="font-size: 0.75rem; color: #8b949e; text-transform: uppercase;">Notified Role</div>
            <div style="font-weight: 700; color: #58a6ff;">{role}</div>
        </div>
    </div>
    <div style="text-align: right;">
        <div style="font-size: 0.75rem; color: #8b949e; text-transform: uppercase;">Urgency Level</div>
        <div style="font-weight: 700; color: {'#f85149' if 'DANGER' in urgency.upper() or 'IMMEDIATE' in urgency.upper() else '#d29922' if 'WARNING' in urgency.upper() else '#3fb950'};">{urgency}</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.caption("IOT-Trace AI Engine v1.2 • Powered by FLAN-T5-Small • © 2026 Wastewater Intelligence")
