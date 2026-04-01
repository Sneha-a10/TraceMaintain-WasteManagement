import streamlit as st
import sys
import os
import subprocess
import json
import datetime
import requests

# -------------------------------------------------
# Path Configuration
# -------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# The integration module is inside the trace-engine folder
sys.path.append(os.path.join(PROJECT_ROOT, "trace-engine"))

from integration.run_live_simulation import run_live_simulation
from trace_engine.rule_engine import RuleEngine

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
# Networking & Live Stream Integration
# -------------------------------------------------
def fetch_live_stream_data():
    """Fetches real-time pure telemetry from the independent network simulator and runs the local Rule Engine."""
    try:
        resp = requests.get("http://localhost:8000/api/latest", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if not data:
                return []
                
            engine = RuleEngine()
            results = []
            for r in data:
                event = {
                    "asset_id": r.get("asset_id", "STP_DEMO"),
                    "timestamp": r.get("timestamp"),
                    "pH": r.get("pH"),
                    "BOD_mg_L": r.get("BOD_mg_L"),
                    "COD_mg_L": r.get("COD_mg_L"),
                    "TSS_mg_L": r.get("TSS_mg_L"),
                    "temperature_C": r.get("temperature_C", 25.0)
                }
                trace, trace_path = engine.evaluate(event)
                results.append({
                    "component": event["asset_id"],
                    "timestamp": event["timestamp"],
                    "features": {
                        "pH": event["pH"],
                        "BOD": event["BOD_mg_L"],
                        "COD": event["COD_mg_L"],
                        "TSS": event["TSS_mg_L"],
                        "Temp": event["temperature_C"]
                    },
                    "trace": trace,
                    "trace_path": trace_path
                })
            return results
    except Exception as e:
        import traceback
        st.error(f"🚨 Critical Failure in fetch_live_stream_data:\n\n{traceback.format_exc()}")
        print(f"Failed to fetch external live stream: {e}")
    return []

# -------------------------------------------------
# State Management
# -------------------------------------------------
# -------------------------------------------------
# State Management
# -------------------------------------------------
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "builtin"
if "simulation_results" not in st.session_state:
    st.session_state.simulation_results = []
if "active_idx" not in st.session_state:
    st.session_state.active_idx = 0
if "cache" not in st.session_state:
    st.session_state.cache = {}
if "selected_live_alert" not in st.session_state:
    st.session_state.selected_live_alert = None
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False

# -------------------------------------------------
# Sidebar Controls
# -------------------------------------------------
with st.sidebar:
    st.title("\u2699\ufe0f Controls")
    
    # 1. Live Network Integration 
    c_btn1, c_btn2 = st.columns([1, 1], gap="small")
    with c_btn1:
        if st.button("\U0001f4e1 Connect Live", type="primary", use_container_width=True):
            st.session_state.app_mode = "live_api"
            st.session_state.auto_refresh = True
            with st.status("Fetching streaming telemetry...", expanded=False):
                st.session_state.simulation_results = fetch_live_stream_data()
                if st.session_state.simulation_results:
                    export_trace_to_llm(st.session_state.simulation_results[0]["trace"])
            st.session_state.selected_live_alert = None
            st.session_state.cache = {}
            st.rerun()
    with c_btn2:
        if st.button("\u23f8\ufe0f Stop Feed", type="secondary", use_container_width=True):
            st.session_state.auto_refresh = False
            st.rerun()
            
    # Auto refresh toggle only in live mode
    if st.session_state.app_mode == "live_api":
        st.session_state.auto_refresh = st.toggle("Auto-Refresh Feed (2s)", value=st.session_state.auto_refresh)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 2. Old Built-in Engine demo
    if st.button("\U0001f680 Built-in Engine Demo", type="secondary", use_container_width=True):
        st.session_state.app_mode = "builtin"
        with st.status("Generating data...", expanded=False):
            st.session_state.simulation_results = run_live_simulation()
            if st.session_state.simulation_results:
                export_trace_to_llm(st.session_state.simulation_results[0]["trace"])
        st.session_state.active_idx = 0
        st.session_state.selected_live_alert = None
        st.session_state.cache = {}
        st.rerun()

    # If built-in mode, show old static event selectors
    if st.session_state.app_mode == "builtin" and st.session_state.simulation_results:
        st.markdown("---")
        st.markdown("### \U0001f4e1 Select Static Event")
        for i in range(len(st.session_state.simulation_results)):
            label = f"Event {i+1} : {st.session_state.simulation_results[i]['trace']['decision']}"
            if st.button(label, use_container_width=True, key=f"btn_{i}", 
                         type="primary" if i == st.session_state.active_idx else "secondary"):
                st.session_state.active_idx = i
                export_trace_to_llm(st.session_state.simulation_results[i]["trace"])
                st.rerun()

# -------------------------------------------------
# Main UI Helpers
# -------------------------------------------------
def render_ai_dashboard(active_data, active_idx, in_sidebar=False):
    """Renders the standard AI analysis dashboard snippet"""
    trace = active_data["trace"]
    features = active_data["features"]

    status_map = {
        "ALARM": {"color": "#f85149", "label": "\U0001f6a8 DANGER"},
        "WARNING": {"color": "#d29922", "label": "\u26a0\ufe0f WARNING"},
        "NORMAL": {"color": "#3fb950", "label": "\u2705 NORMAL"},
    }
    config = status_map.get(trace["decision"], status_map["NORMAL"])

    st.markdown(f"""
    <div class="header-container" style="padding: 10px; font-size: 0.8rem;">
        <div class="asset-id">{active_data['component']} • {active_data['timestamp'][:19]}</div>
        <div class="status-text" style="color: {config['color']}; text-align: center;">{config['label']}</div>
    </div>
    """, unsafe_allow_html=True)

    # Run AI Pipeline if needed
    if active_idx not in st.session_state.cache:
        with st.spinner("\U0001f9e0 AI interpreting trace..."):
            export_trace_to_llm(trace)
            st.session_state.cache[active_idx] = run_ai_pipeline()
        st.rerun()

    ai_results = st.session_state.cache[active_idx]

    # Content generation helper
    def draw_readings():
        st.markdown("""<div class="panel-title">📡 Sensor Readings</div>""", unsafe_allow_html=True)
        m1, m2 = st.columns(2)
        m3, m4 = st.columns(2)
        with m1: st.metric("pH", f"{features['pH']:.2f}")
        with m2: st.metric("BOD", f"{features['BOD']:.1f}", delta=f"{features['BOD']-30:.1f}" if features['BOD']>30 else None, delta_color="inverse")
        with m3: st.metric("COD", f"{features['COD']:.1f}")
        with m4: st.metric("Temp", f"{features['Temp']:.1f}")
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""<div class="panel-title">🔗 Decision Reasoning (Trace)</div>""", unsafe_allow_html=True)
        reasoning = trace.get("reasoning_trace", [])
        if reasoning:
            html = '<div class="reasoning-list">'
            for item in reasoning:
                html += f'<div class="reasoning-item" style="font-size: 0.8rem;">{item}</div>'
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown('<div class="reasoning-item item-normal">All sensor values within regulatory compliance limits.</div>', unsafe_allow_html=True)

    def draw_ai():
        st.markdown("""<div class="panel-title">🤖 Expert Interpretation</div>""", unsafe_allow_html=True)
        explanation = ai_results.get("explanation", "Generating...")
        st.markdown(f'<div class="narrative-box" style="font-size: 0.8rem;">{explanation}</div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""<div class="panel-title">🛠️ Recommended Action Plan</div>""", unsafe_allow_html=True)
        actions = ai_results.get("recommended_action", ["No specific regulatory notes found."])
        for act in actions:
            st.markdown(f"<span style='font-size: 0.8rem;'>- {act}</span>", unsafe_allow_html=True)

    if in_sidebar:
        draw_readings()
        st.markdown("<br>", unsafe_allow_html=True)
        draw_ai()
    else:
        col1, col2 = st.columns([1, 1.5], gap="large")
        with col1: draw_readings()
        with col2: draw_ai()

    st.markdown("<br>", unsafe_allow_html=True)
    plan = ai_results.get("dispatch_plan", {})
    role = plan.get("role", "Operations Team")
    urgency = plan.get("urgency", "Normal")

    st.markdown(f"""
    <div class="resp-footer" style="padding: 10px;">
        <div style="font-size: 0.75rem; color: #8b949e; text-transform: uppercase;">Notified Role: <span style="font-weight: 700; color: #58a6ff;">{role}</span></div>
        <div style="font-size: 0.75rem; color: #8b949e; text-transform: uppercase;">Urgency: <span style="font-weight: 700; color: {'#f85149' if 'DANGER' in urgency.upper() or 'IMMEDIATE' in urgency.upper() else '#d29922' if 'WARNING' in urgency.upper() else '#3fb950'};">{urgency}</span></div>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# Dynamically draw AI Dashboard in Sidebar
# -------------------------------------------------
with st.sidebar:
    if st.session_state.app_mode == "live_api" and st.session_state.selected_live_alert:
        st.markdown("---")
        st.markdown("### 🔍 Live Alert AI Drill-Down")
        active_data = st.session_state.selected_live_alert
        idx_str = f"live_{active_data['timestamp']}"
        render_ai_dashboard(active_data, idx_str, in_sidebar=True)

# -------------------------------------------------
# Main Dashboard UI
# -------------------------------------------------

if st.session_state.app_mode == "builtin":
    # --- BUILT-IN STATIC MODE ---
    if not st.session_state.simulation_results:
        with st.status("\U0001f680 Initializing Wastewater Monitoring Engine...", expanded=True):
            st.write("Generating live sensor simulation (BOD Spike Scenario)...")
            st.session_state.simulation_results = run_live_simulation()
            if st.session_state.simulation_results:
                export_trace_to_llm(st.session_state.simulation_results[0]["trace"])
                st.write("\u2705 Ready! Loading dashboard...")
        st.rerun()

    active_data = st.session_state.simulation_results[st.session_state.active_idx]
    render_ai_dashboard(active_data, str(st.session_state.active_idx))
    st.caption("IOT-Trace AI Engine v1.2 • Powered by FLAN-T5-Small • © 2026 Wastewater Intelligence")

else:
    # --- LIVE API COMMAND CENTER MODE ---
    st.markdown("<h1>\U0001f310 Live Stream Command Center</h1>", unsafe_allow_html=True)
    
    # Auto-fetch if auto-refresh is on
    if st.session_state.auto_refresh:
        st.session_state.simulation_results = fetch_live_stream_data()
    
    live_data = st.session_state.simulation_results
    
    if not live_data:
        st.warning("No data arriving from API. Is `mock_backend.py` running and simulator publishing `run_simulation.py --mode stream`?")
    else:
        # Sort so the newest items are at the top of the feed and queues
        sorted_data = list(reversed(live_data))
        alerts = [item for item in sorted_data if item['trace']['decision'] in ('ALARM', 'WARNING')]
        
        c1, c2 = st.columns([1, 1], gap="small")
        
        with c1:
            st.markdown("### 🚨 Active Actionable Alerts Queue")
            if not alerts:
                st.info("✅ All systems perfectly normal. No alerts currently triggered.")
            else:
                for idx, alert in enumerate(alerts):
                    asset = alert['component']
                    dec = alert['trace']['decision']
                    color = "🔴" if dec == "ALARM" else "🟡"
                    tstamp = alert.get("timestamp", idx)
                    
                    if st.button(f"{color} {asset} - {dec} (Click for AI Analysis)", key=f"alert_{tstamp}_{asset}_{idx}", use_container_width=True):
                        st.session_state.selected_live_alert = alert
                        
        with c2:
            st.markdown("### 📡 Raw Live Telemetry Feed (All Devices)")
            feed_lines = []
            for item in sorted_data:
                time_str = item.get("timestamp", "00:00:00")
                asset = item['component']
                pH = f"{item['features']['pH']:.2f}"
                flow = f"{item['features']['Temp']:.1f}" # Since flow isn't in features properly mapped, we'll just show pH and BOD
                mark = "\u2705" if item['trace']['decision'] == "NORMAL" else "\u26a0\ufe0f"
                feed_lines.append(f"{mark} [{time_str}] {asset:<15} | pH={pH}  BOD={item['features']['BOD']:>4.1f}  [{item['trace']['decision']}]")
                
            feed_text = "\n".join(feed_lines)
            st.code(feed_text, language="shell")
            
        st.markdown("---")
            
    st.caption("Live Feed Command Center • Polls http://localhost:8000/api/latest via API")

# -------------------------------------------------
# Background Auto-Refresh Loop
# -------------------------------------------------
if getattr(st.session_state, "app_mode", None) == "live_api" and getattr(st.session_state, "auto_refresh", False):
    import time
    time.sleep(2)
    st.rerun()
