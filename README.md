# 🌍 Smart Campus Wastewater Monitoring & AI Command Center

An advanced, end-to-end IoT simulation and Artificial Intelligence monitoring system for campus wastewater treatment plants (STPs). This project acts as a live command center, ingesting simulated telemetry data, instantly evaluating it through a custom Rule Engine, and using an offline Language Model to generate expert compliance narratives and action plans.

---

## 🏗️ System Architecture

The project is broken into three main distinct components that work together over a local network:

1. **IoT Telemetry Generator (`data-n-sensor`)**
   Simulates 4 independent hardware assets across the campus (STP_HOSTEL_A, STP_HOSTEL_B, STP_LAB_BLOCK, and STP_CANTEEN). It generates realistic wastewater patterns (pH, BOD, COD, flow rate) and simulates disaster scenarios (Contamination Spikes, pH Drifts, etc.) by transmitting JSON payloads via HTTP POST.

2. **Mock IoT Backend (`mock_backend.py`)**
   A lightweight, vanilla Python HTTP Server acting as the ingestion API bridge. It listens on port `8000`, receives incoming POST requests from the sensors, and stores a rolling window of the last 200 logs. It provides a visual HTML dashboard and a JSON API (`/api/latest`) for the primary website to ingest.

3. **Streamlit AI Command Center (`ui/app.py` + `trace-engine`)**
   The main user interface. It connects to the Live API, polls for incoming telemetry, and runs every single reading through a custom `RuleEngine`. If anomalies are detected (WARNING or ALARM), it utilizes an onboard Language Model (FLAN-T5-Small via Hugging Face pipelines) to generate an expert interpretation, reference regulatory compliance targets (like CPCB OCEMS standards), and recommend dispatch plans.

---

## 🚀 How to Run the Project (Live Stream Mode)

To run the complete Live IoT capability, you need to open **three separate terminals** in your root project folder (`TraceMaintain-WasteManagement`).

### Terminal 1: Start the Backend Server
This runs the local API that receives data from the sensors and serves the Website.
```powershell
python mock_backend.py
```
*Note: You can view a raw, standalone visual representation of the logs by visiting `http://localhost:8000` in your browser.*

### Terminal 2: Start the IoT Sensor Simulation
This script will start rapidly generating sensor data on multiple threads and firing it at the backend server.
```powershell
cd data-n-sensor
python run_simulation.py --mode stream --endpoint http://localhost:8000/ingest --interval 5
```
*Pro-tip: For a hackathon presentation, you can change `--interval 5` to `--interval 2` or `1` so that data pours in incredibly fast. The system is programmed to start throwing disasters (like Contamination Spikes and High pH) within the first 30 seconds.*

### Terminal 3: Start the Streamlit Command Center
This runs the beautiful dashboard where you actually view the AI analytics.
```powershell
python -m streamlit run ui/app.py
```

### Navigating the UI
1. Look at your left sidebar and click **"📡 Connect Live"**.
2. Toggle the **"Auto-Refresh Feed (2s)"** to ON. 
3. Watch the raw feed scroll on the right side of the screen.
4. When an anomaly drops (indicated by a 🔴 or 🟡 dot), it will appear in the **Active Actionable Alerts Queue** on the left.
5. Click any alert button in that queue to generate a deep-dive AI report in the sidebar!

---

## 🧭 File Directory Guide

- `mock_backend.py` -> The HTTP routing logic and memory storage for the network stream.
- `ui/app.py` -> The fully styled Streamlit interface. Handles UI state, layouts, and data rendering.
- `trace-engine/` -> Contains the AI logic.
  - `rule_engine.py` -> Evaluates raw sensor floats against strict logic thresholds to generate an ALARM/WARNING/NORMAL decision.
  - `integration/run_live_simulation.py` -> Coordinates the AI inference logic.
- `data-n-sensor/` -> The heavy IoT simulation logic.
  - `run_simulation.py` -> Central orchestrator for the threads/workers.
  - `data_stream.py` -> Defines the `DEFAULT_CAMPUS_SCHEDULE` which controls exactly when normal behaviors become disaster scenarios in the timeline.
  - `network_client.py` -> The internal HTTP mechanism that fires JSON requests to `localhost:8000`.

---

## 🛑 Common Troubleshooting

- **"No module named 'xyz'"**: Ensure you are in your active Python environment and have run `pip install -r requirements.txt`. (Requires `streamlit`, `transformers`, `torch`, `requests`).
- **"Port 8000 already in use"**: The mock backend from a previous run is still alive. Open powershell and forcefully kill it: `Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force`.
- **Dashboard is blank after clicking Connect Live**: Ensure your backend and your Streamlit server are running simultaneously, AND you have toggled the *Auto-Refresh* switch to ON.
- **Data is only "NORMAL"**: The simulation is designed realistically so anomalies happen over a span of minutes. If you want anomalies to happen instantly, open `data-n-sensor/data_stream.py` and modify the `tick` values inside `DEFAULT_CAMPUS_SCHEDULE` to be smaller numbers. (Currently configured to crash hard within 60 seconds of boot!)

---
*Created by the TraceMaintain Smart Campus Team (2026).*
