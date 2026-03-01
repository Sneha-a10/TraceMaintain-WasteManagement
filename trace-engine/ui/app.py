import streamlit as st
import sys
import os
import subprocess
import json

# -------------------------------------------------
# Make trace-engine importable
# -------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

from integration.run_live_simulation import run_live_simulation


# -------------------------------------------------
# Streamlit Page Config & Theme
# -------------------------------------------------
st.set_page_config(
    page_title="Industrial Trace Engine Desktop Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS to strictly match the reference image
st.markdown("""
<style>
    /* 1. Global Reset & Dark Theme */
    .stApp {
        background-color: #0d1117;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        color: #c9d1d9;
    }
    
    /* 2. Controls & Widgets */
    .stButton > button {
        background-color: #1f6feb;
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        padding: 0.5rem 1rem;
    }
    .stButton > button:hover {
        background-color: #388bfd;
    }
    .stButton > button:disabled {
        background-color: #161b22;
        color: #484f58;
        border: 1px solid #30363d;
    }
    
    .feature-key { color: #d2a8ff; font-weight: 500; }
    .feature-val { color: #f0f6fc; font-weight: 700; font-family: monospace; }
    
    /* Run Simulation Button - Teal with White Border */
    .stButton:has(+ div .run-marker) button {
        background-color: #009688 !important;
        border: 1.5px solid #ffffff !important;
        color: white !important;
    }
    .stButton:has(+ div .run-marker) button:hover,
    .stButton:has(+ div .run-marker) button:active,
    .stButton:has(+ div .run-marker) button:focus {
        background-color: #00bfa5 !important;
        border-color: #ffffff !important;
        color: white !important;
        box-shadow: 0 0 10px rgba(0, 150, 136, 0.4) !important;
    }
    
    /* 3. Status Banner (Red Strip) */
    .status-banner {
        width: 100%;
        padding: 1rem 2rem;
        margin-top: 0;
        margin-bottom: 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: white;
        font-weight: bold;
        border-radius: 4px;
    }
    .banner-danger { background-color: #da3633; box-shadow: 0 4px 12px rgba(218, 54, 51, 0.2); }
    .banner-normal { background-color: #238636; box-shadow: 0 4px 12px rgba(35, 134, 54, 0.2); }
    .banner-borderline { background-color: #d29922; color: #1a1a1a; }

    /* 4. Panels (Cards) */
    .panel-container {
        background-color: #0d1117; /* Matches bg, distinct by layout */
        border: 1px solid #30363d; /* Subtle border */
        border-radius: 6px;
        padding: 0;
        overflow: hidden;
        height: 100%;
        box-shadow: 0 0 0 1px #30363d;
    }
    .panel-header {
        background-color: #161b22;
        padding: 1rem;
        border-bottom: 1px solid #30363d;
        font-weight: 600;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 0.85rem;
        display: flex;
        align-items: center;
    }
    .panel-icon { margin-right: 8px; }
    
    /* 4a. Left Panel: Features */
    .feature-list {
        padding: 1rem;
    }
    .feature-item {
        display: flex;
        justify-content: space-between;
        padding: 12px 0;
        border-bottom: 1px solid #21262d;
        font-size: 0.95rem;
    }
    .feature-key { color: #d2a8ff; font-weight: 700; }
    .feature-val { color: #f0f6fc; font-weight: 700; font-family: monospace; }
    
    /* 4b. Right Panel: Trace Steps */
    .trace-container {
        padding: 1.5rem;
    }
    .trace-step {
        background-color: #0d1117;
        border: 1px solid #21262d;
        border-radius: 6px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        position: relative;
    }
    .trace-step-header {
        display: flex;
        align-items: center;
        margin-bottom: 10px;
    }
    .step-circle {
        background-color: #1f6feb;
        color: white;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.8rem;
        font-weight: bold;
        margin-right: 12px;
    }
    .node-name {
        color: #8b949e;
        font-weight: 700;
        font-size: 0.85rem;
        text-transform: uppercase;
    }
    .logic-box {
        background-color: #0d1117;
        padding: 8px 0;
        font-family: monospace;
        font-size: 1.1rem;
        color: #e6edf3;
    }
    .val-highlight { color: #ff7b72; font-weight: bold; } /* Red for values */
    .result-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: bold;
        text-transform: uppercase;
        margin-right: 8px;
    }
    .res-fired { background-color: #3b2323; color: #ff7b72; border: 1px solid #ff7b72; }
    .res-pass { background-color: #1a2e23; color: #3fb950; border: 1px solid #3fb950; }
    
    /* 5. Custom Tabs (Buttons) */
    .tab-row {
        display: flex;
        gap: 10px;
        margin-bottom: 1rem;
    }
    
    /* Footer */
    .footer-bar {
        margin-top: 3rem;
        border-top: 1px solid #30363d;
        padding-top: 1rem;
        display: flex;
        justify-content: space-between;
        color: #484f58;
        font-size: 0.75rem;
        font-family: sans-serif;
        font-weight: 600;
    }
    
    /* Bounding Box Style */
    .content-box {
        background-color: #0d1117;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .content-box-header {
        margin-bottom: 1rem;
        border-bottom: 1px solid #30363d;
        padding-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------
# State Management
# -------------------------------------------------
def export_trace_to_llm(trace, component="UNKNOWN"):
    """Saves the current trace to the mt-llm knowledge base for processing."""
    llm_input_path = os.path.join(PROJECT_ROOT, "..", "mt-llm", "knowledge_base", "post_decision_trace.json")
    try:
        os.makedirs(os.path.dirname(llm_input_path), exist_ok=True)
        # Ensure component is in the trace
        trace_copy = trace.copy()
        if "component" not in trace_copy:
            trace_copy["component"] = component
        # Wrap in expected format
        data = {"input_trace": trace_copy}
        with open(llm_input_path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        st.error(f"Failed to export trace: {e}")

if "simulation_results" not in st.session_state:
    st.session_state.simulation_results = []
    
if "active_event_idx" not in st.session_state:
    st.session_state.active_event_idx = 0
    st.session_state.last_exported_idx = -1 # Track export state

if "ai_analysis_cache" not in st.session_state:
    st.session_state.ai_analysis_cache = {} # Cache idx -> results

if "ai_feedback_state" not in st.session_state:
    st.session_state.ai_feedback_state = {} # Cache idx -> "Accepted" | "Rejected"

def handle_ai_feedback(idx, status):
    """Processes user feedback (Accept/Reject) for a specific AI advisory."""
    st.session_state.ai_feedback_state[idx] = status
    
    if status == "Accepted":
        # Run the KB update script in the background
        base_path = os.path.join(PROJECT_ROOT, "..", "mt-llm")
        kb_update_script = os.path.join(base_path, "pipeline_logic", "machine_explainer.py")
        env = os.environ.copy()
        env["ACTION"] = "UPDATE_KB"
        env["NON_INTERACTIVE"] = "1"
        try:
            subprocess.run([sys.executable, kb_update_script], cwd=base_path, env=env, capture_output=True)
        except:
            pass

def run_ai_pipeline():
    """Runs the mt-llm pipeline scripts and returns the result."""
    env = os.environ.copy()
    env["NON_INTERACTIVE"] = "1"
    
    # Resolve correct Python interpreter
    python_exe = sys.executable

    base_path = os.path.join(PROJECT_ROOT, "..", "mt-llm")
    input_trace = os.path.join(base_path, "knowledge_base", "post_decision_trace.json")
    rag_script = os.path.join(base_path, "pipeline_logic", "process_alert_workflow.py")
    exp_script = os.path.join(base_path, "pipeline_logic", "machine_explainer.py")
    route_script = os.path.join(base_path, "pipeline_logic", "routing_agent.py")
    
    if not os.path.exists(input_trace):
        return {"error": f"Input trace missing at {input_trace}"}

    try:
        # 1. Run RAG Workflow
        rag_res = subprocess.run([python_exe, rag_script], cwd=base_path, env=env, capture_output=True, text=True)
        if rag_res.returncode != 0:
            return {"error": f"RAG Stage Failed: {rag_res.stderr}"}
            
        # 2. Run Machine Explainer
        exp_res = subprocess.run([python_exe, exp_script], cwd=base_path, env=env, capture_output=True, text=True)
        if exp_res.returncode != 0:
            return {"error": f"Explainer Stage Failed: {exp_res.stderr}"}
            
        # 3. Run Routing Agent
        route_res = subprocess.run([python_exe, route_script], cwd=base_path, env=env, capture_output=True, text=True)
        if route_res.returncode != 0:
            return {"error": f"Routing Stage Failed: {route_res.stderr}"}
        
        # 4. Load Results
        rec_path = os.path.join(base_path, "final_recommendation.json")
        exp_path = os.path.join(base_path, "ai_explanation.json")
        route_path = os.path.join(base_path, "dispatch_plan.json")
        
        recs = {}
        if os.path.exists(rec_path):
            with open(rec_path, 'r') as f: recs = json.load(f)
        
        expl = {}
        if os.path.exists(exp_path):
            with open(exp_path, 'r') as f: expl = json.load(f)
            
        plan = {}
        if os.path.exists(route_path):
            with open(route_path, 'r') as f: plan = json.load(f)
            
        # Create a payload format expected by UI
        return {**recs, **expl, "dispatch_plan": plan}
    except Exception as e:
        return {"error": str(e)}


# -------------------------------------------------
# UI Components
# -------------------------------------------------
def render_header():
    # Centered, UPPERCASE Header
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0 2rem 0;">
        <h1 style="
            text-transform: uppercase; 
            font-size: 2.2rem; 
            font-weight: 800; 
            letter-spacing: 2px;
            color: #e6edf3;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        ">
            <span style="margin-right: 16px;">📊</span> Industrial Trace Engine Desktop Dashboard
        </h1>
    </div>
    """, unsafe_allow_html=True)

def render_llm_panel(trace):
    idx = st.session_state.active_event_idx
    cache = st.session_state.ai_analysis_cache
    feedback = st.session_state.ai_feedback_state
    
    if idx not in cache:
        # Automatic trigger with status message
        with st.status("🧠 Analyzing decision trace and manuals...", expanded=True) as status:
            results = run_ai_pipeline()
            st.session_state.ai_analysis_cache[idx] = results
            status.update(label="✅ Advisory Generated", state="complete", expanded=False)
            st.rerun()
    else:
        # Show results
        res = cache[idx]
        if "error" in res:
            st.error(f"AI Pipeline Error: {res['error']}")
            return

        explanation = res.get("explanation", "No explanation generated.")
        recs = res.get("recommended_action", [])
        safety = res.get("safety_note", "No safety note provided.")
        ref = res.get("reference", "Internal Knowledge Base")
        plan = res.get("dispatch_plan", {})
        
        assigned_team = plan.get("assigned_team", "N/A")
        priority = plan.get("priority", "N/A")
        route_steps = plan.get("route_steps", [])

        # Consolidate HTML for absolute structure (Remove indentation to avoid MD code blocks)
        html = f"""<div class="content-box">
<div class="panel-header content-box-header">
<span class="panel-icon">🤖</span> AI ANALYSIS & ADVISORY
</div>
<div style="margin-bottom: 1.5rem;">
<div style="color: #d2a8ff; font-weight: 700; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 8px;">AI Narrative</div>
<div style="color: #e6edf3; font-style: italic; line-height: 1.5; background: rgba(210, 168, 255, 0.05); padding: 1rem; border-radius: 6px; border-left: 3px solid #d2a8ff;">
"{explanation}"
</div>
</div>
<div style="margin-bottom: 1.5rem;">
<div style="color: #3fb950; font-weight: 700; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 8px;">Recommended Actions</div>
<div style="color: #f0f6fc; font-size: 0.9rem;">"""
        for r in recs:
            html += f'<div style="margin-bottom: 6px; display: flex;"><span style="color: #3fb950; margin-right: 8px;">•</span> {r}</div>'
        
        html += f"""</div>
</div>
<div style="margin-bottom: 1.5rem; background: rgba(31, 111, 235, 0.05); padding: 1rem; border-left: 3px solid #1f6feb; border-radius: 6px;">
<div style="color: #1f6feb; font-weight: 700; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 8px;">Dispatch Plan</div>
<div style="color: #e6edf3; font-size: 0.9rem; margin-bottom: 8px;">
<strong>Team:</strong> {assigned_team} &nbsp; | &nbsp; <strong>Priority:</strong> <span style="color: {'#ff7b72' if priority in ['HIGH', 'CRITICAL'] else '#d29922' if priority == 'MEDIUM' else '#3fb950'};">{priority}</span>
</div>
<div style="color: #f0f6fc; font-size: 0.85rem;">"""
        if route_steps:
            for s in route_steps:
                html += f'<div style="margin-bottom: 4px;"><strong>Step {s["step"]}:</strong> {s["instruction"]}</div>'
        else:
            html += f'<div>No routing required.</div>'
            
        html += f"""</div>
</div>
<div style="padding: 10px; background: rgba(218, 54, 51, 0.1); border: 1px solid #da3633; border-radius: 6px; margin-bottom: 0.5rem;">
<div style="color: #ff7b72; font-weight: bold; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 4px;">⚠ Safety Note</div>
<div style="color: #f0f6fc; font-size: 0.85rem;">{safety}</div>
</div>
<div style="color: #8b949e; font-size: 0.75rem; display: flex; justify-content: space-between; padding-top: 1rem; border-top: 1px solid #30363d; margin-top: 1rem;">
<span>Source: {ref}</span>
<span>Powered by FLAN-T5-Small</span>
</div>
</div>"""
        st.markdown(html, unsafe_allow_html=True)
        
        # Feedback Buttons Row - ONLY if NOT NORMAL
        decision = trace.get("decision", "NORMAL")
        if decision != "NORMAL":
            if idx not in feedback:
                st.markdown('<div style="margin-top: 1rem;"></div>', unsafe_allow_html=True)
                f_col1, f_col2 = st.columns(2)
                with f_col1:
                    if st.button("✅ ACCEPT", key=f"acc_{idx}", use_container_width=True):
                        handle_ai_feedback(idx, "Accepted")
                        st.rerun()
                with f_col2:
                    if st.button("❌ REJECT", key=f"rej_{idx}", use_container_width=True):
                        handle_ai_feedback(idx, "Rejected")
                        st.rerun()
            else:
                status_color = "#3fb950" if feedback[idx] == "Accepted" else "#da3633"
                st.markdown(f"""
                    <div style="text-align: center; color: {status_color}; font-weight: bold; padding: 0.5rem; border: 1px solid {status_color}; border-radius: 4px; margin-top: 1rem;">
                        Feedback Recorded: {feedback[idx]}
                    </div>
                """, unsafe_allow_html=True)

def render_status_banner(trace, component):
    decision = trace.get("decision", "UNKNOWN")
    conf = trace.get("final_confidence", 0.0)
    
    css_class = "banner-normal"
    if decision == "DANGER": css_class = "banner-danger"
    elif decision == "BORDERLINE": css_class = "banner-borderline"
    
    # 3. STATUS BANNER
    st.markdown(f"""
    <div class="status-banner {css_class}">
        <div style="font-size: 1.25rem; display: flex; align-items: center;">
            <span style="font-size: 1.5rem; margin-right: 12px;">⚠</span> 
            STATUS: {decision}
            <span style="opacity: 0.6; margin: 0 1rem;">|</span>
            <span style="font-size: 1rem; font-weight: normal;">Severity Score: {conf:.2f}</span>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 0.7rem; opacity: 0.8; letter-spacing: 1px;">ACTIVE MONITORING</div>
            <div style="font-size: 1rem;">COMPONENT: {component}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_features_panel(result):
    # Construct FULL HTML string including the bounding box
    html = '<div class="content-box">'
    
    # Internal Header
    html += """
    <div class="panel-header content-box-header">
        <span class="panel-icon">📡</span> EXTRACTED FEATURES
    </div>
    """
    
    # Content
    html += '<div class="feature-list">'
    features = result["features"]
    for k, v in features.items():
        html += f'<div class="feature-item"><span class="feature-key">{k}</span><span class="feature-val">{v}</span></div>'
    html += '</div></div>' # Close content and box
    
    st.markdown(html, unsafe_allow_html=True)

def render_trace_panel(trace):
    # Start Box
    full_html = '<div class="content-box">'
    
    # Header
    full_html += """
    <div class="panel-header content-box-header">
        <span class="panel-icon">🔗</span> DECISION TRACE & REASONING
    </div>
    """
    
    # Steps
    reasoning = trace.get("reasoning_trace", [])
    for i, step in enumerate(reasoning, 1):
        rule = step.get("rule", "UNKNOWN")
        feature_name = step.get("feature", "unknown_sensor")
        val = step.get("feature_value", 0)
        thresh = step.get("threshold", 0)
        comp = step.get("comparison", ">")
        res = step.get("rule_result", "N/A")
        cond_text = "Condition check"
        if res == "FIRED": cond_text = "Threshold exceeded"
        
        res_class = "res-fired" if res == "FIRED" else "res-pass"
        val_style = "val-highlight" if res == "FIRED" else ""
        
        step_html = f'<div class="trace-step">'
        step_html += f'<div class="trace-step-header"><span class="step-circle">{i}</span><span class="node-name">NODE: {rule}</span></div>'
        step_html += f'<div class="logic-box"><span style="font-size: 0.8em; color: #8b949e; margin-right: 8px;">[SENSOR: {feature_name}]</span> Value: <span class="{val_style}">{val}</span> {comp} Threshold: {thresh}</div>'
        step_html += f'<div style="margin-top: 8px; display: flex; align-items: center;"><span class="result-badge {res_class}">RESULT: {res}</span><span style="font-size: 0.8rem; color: #8b949e;">Condition: {cond_text}</span></div>'
        step_html += '</div>'
        full_html += step_html
        
    full_html += '</div>' # Close Box
    st.markdown(full_html, unsafe_allow_html=True)


# -------------------------------------------------
# Main Layout Logic
# -------------------------------------------------
render_header()

# Initialize results variable safe-guarded
results = st.session_state.simulation_results

# 2. CONTROLS (Events Left, Run Right) - ALWAYS RENDERED
st.markdown("---")
col_controls, col_run = st.columns([3, 1])

with col_controls:
    if results:
        # Event Buttons - Aligned horizontally
        cols = st.columns(3)
        def set_tab(idx): st.session_state.active_event_idx = idx
        
        for i in range(3):
            if i < len(results):
                label = f"Event {i+1}"
                is_active = (i == st.session_state.active_event_idx)
                if cols[i].button(label, key=f"tab_{i}", type="primary" if is_active else "secondary", use_container_width=True):
                    set_tab(i)
                    # Export the clicked trace
                    export_trace_to_llm(results[i]["trace"], results[i].get("component"))
                    st.rerun()
            else:
                cols[i].button(f"Event {i+1}", disabled=True, key=f"tab_disable_{i}", use_container_width=True)

with col_run:
     # No container, button first for perfect alignment
     if st.button("▶ Run Simulation", type="primary", use_container_width=True):
        with st.spinner("Loading..."):
            st.session_state.simulation_results = run_live_simulation()
            # Export the first trace immediately
            if st.session_state.simulation_results:
                first_res = st.session_state.simulation_results[0]
                export_trace_to_llm(first_res["trace"], first_res.get("component"))
        st.session_state.active_event_idx = 0
        st.rerun()
     # Marker after button to anchor CSS strictly to this column
     st.markdown('<div class="run-marker"></div>', unsafe_allow_html=True)

# 3. CONTENT (Only if results exist)
if results:
    # Validation of index
    if st.session_state.active_event_idx >= len(results):
        st.session_state.active_event_idx = 0
        
    active_res = results[st.session_state.active_event_idx]
    active_trace = active_res["trace"]
    # --- PROCEED WITH LAYOUT ---

    # 3. STATUS BANNER (Full Width)
    # We use a container to span width
    with st.container():
        st.markdown('<div style="margin-top: 1rem;"></div>', unsafe_allow_html=True) # Spacer
        render_status_banner(active_trace, active_res["component"])
        st.markdown('<div style="margin-bottom: 2rem;"></div>', unsafe_allow_html=True) # Spacer

    # 4. CONTENT GRID (2 Columns)
    grid_left, grid_right = st.columns(2)
    
    # --- LEFT COLUMN CONTENT ---
    with grid_left:
        # BOX 1: EXTRACTED FEATURES
        render_features_panel(active_res)
        
        # BOX 2: RAW TRACE DATA
        # Manual Box Construction
        json_html = '<div class="content-box">'
        json_html += '<div class="panel-header content-box-header"><span class="panel-icon">📜</span> RAW TRACE DATA</div>'
        json_html += '<div style="height: 300px; overflow-y: auto; padding-right: 10px;">'
        for k, v in active_trace.items():
            disp_val = v
            if isinstance(v, (dict, list)):
                sanitized_val = str(v).replace("<", "&lt;").replace(">", "&gt;")
                disp_val = f"<span style='opacity:0.6; font-size:0.85em;'>{sanitized_val}</span>"
            json_html += f'<div class="feature-item"><span class="feature-key">{k}</span><span class="feature-val">{disp_val}</span></div>'
        json_html += "</div></div>" # Close list and box
        st.markdown(json_html, unsafe_allow_html=True)

    # --- RIGHT COLUMN CONTENT ---
    with grid_right:
        # BOX 3: LLM
        render_llm_panel(active_trace)
        
        # BOX 4: DECISION TRACE
        render_trace_panel(active_trace)
        
    # FOOTER
    st.markdown("""
    <div class="footer-bar">
        <div>IOT-TRACE ENGINE v1.0.4</div>
        <div>STATUS: ONLINE • LAST UPDATE: NOW</div>
    </div>
    """, unsafe_allow_html=True)

else:
    # Empty State
    st.info("System Ready. Click 'Run Simulation' to begin analysis.")
