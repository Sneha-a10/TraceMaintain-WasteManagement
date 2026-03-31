import json
from http.server import BaseHTTPRequestHandler, HTTPServer

# Store the latest data from each simulated device
recent_data = {}

class IngestHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        """Serve a dashboard or return raw telemetry JSON"""
        if self.path == '/api/latest':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(list(recent_data.values())).encode('utf-8'))
            return
            
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        cards = ""
        for device, data in recent_data.items():
            cards += f"""
            <div style="border: 1px solid #334155; padding: 20px; margin: 10px; border-radius: 12px; background: #1e293b; color: white; width: 320px; display: inline-block; vertical-align: top; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <h2 style="margin-top:0; color: #38bdf8; border-bottom: 1px solid #334155; padding-bottom: 10px;">{device}</h2>
                <div style="font-size: 1.1em; line-height: 1.6;">
                    <p style="margin: 5px 0;"><b>pH Level:</b> <span style="color: #a7f3d0;">{data.get('pH')}</span></p>
                    <p style="margin: 5px 0;"><b>Flow Rate:</b> <span style="color: #fca5a5;">{data.get('flow_rate_m3_hr')} m³/hr</span></p>
                    <p style="margin: 5px 0;"><b>COD:</b> <span style="color: #fef08a;">{data.get('COD_mg_L')} mg/L</span></p>
                    <p style="margin: 5px 0;"><b>BOD:</b> <span style="color: #cbd5e1;">{data.get('BOD_mg_L')} mg/L</span></p>
                    <p style="margin: 5px 0;"><b>TSS:</b> <span style="color: #cbd5e1;">{data.get('TSS_mg_L')} mg/L</span></p>
                </div>
                <div style="margin-top: 15px; padding: 8px; background: #0f172a; border-radius: 6px; font-size: 0.85em; color: #94a3b8;">
                    <strong>Active Scenario:</strong> {data.get('scenario')}
                </div>
            </div>
            """
            
        html = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta http-equiv="refresh" content="2">
                <title>IoT Wastewater Dashboard</title>
                <style>
                    body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: white; padding: 40px; margin: 0; }}
                    h1 {{ color: #f8fafc; font-weight: 300; font-size: 2.5em; letter-spacing: -1px; }}
                    .container {{ display: flex; flex-wrap: wrap; gap: 10px; }}
                </style>
            </head>
            <body>
                <h1>🟢 Live IoT Telemetry Dashboard</h1>
                <p style="color: #94a3b8; margin-bottom: 30px;">Auto-refreshing every 2 seconds matching stream intervals...</p>
                
                <div class="container">
                    {cards if cards else '<p style="color: #fcd34d; font-size: 1.2em; padding: 20px;">⏱️ Waiting for sensor stream data... Run your python stream!</p>'}
                </div>
            </body>
        </html>
        """
        self.wfile.write(html.encode('utf-8'))

    def do_POST(self):
        """Receive JSON sensor payloads natively sent by the simulation"""
        if self.path == '/ingest':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
                device = payload.get('device_id', 'UNKNOWN')
                
                # Store the latest reading in memory for the Dashboard to render
                recent_data[device] = payload
                
                print(f"[\u2193 INGESTED] {device: <15} | pH: {payload.get('pH', '?'):<5} | Flow: {payload.get('flow_rate_m3_hr', '?'):<6} | Scenario: {payload.get('scenario')}")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
                
            except Exception as e:
                print(f"[ERROR] Failed to parse payload: {e}")
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress the default verbose HTTP server logs so we only see our clean prints
        pass

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, IngestHandler)
    
    print("======================================================")
    print(f"  MOCK IOT BACKEND + DASHBOARD RUNNING")
    print(f"  \U0001f310 Open browser at:  http://localhost:{port}")
    print(f"  \u25b6 API Endpoint at:   http://localhost:{port}/ingest")
    print("======================================================\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down backend server...")
        httpd.server_close()

if __name__ == '__main__':
    run_server()
