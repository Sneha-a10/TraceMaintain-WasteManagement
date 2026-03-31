# -*- coding: utf-8 -*-
"""
network_client.py
=================
Smart Campus Wastewater Monitoring System
IoT Network Streaming Client

Responsibilities:
  - Takes raw telemetry JSON.
  - Adds IoT device metadata (device_id, location, device_type).
  - POSTs data to a configurable API endpoint using `requests`.
  - Implements basic error handling, timeout, and a 1-retry mechanism.
  - Degrades gracefully without crashing the simulation on network failure.

NOTE: This layer only transmits data. No threshold or compliance logic exists here.
"""

import requests
import json
import time

class IoTNetworkClient:
    def __init__(self, endpoint: str, max_retries: int = 1, timeout: float = 5.0):
        self.endpoint = endpoint
        self.max_retries = max_retries
        self.timeout = timeout
        
    def _enrich_payload(self, reading: dict) -> dict:
        """Adds device realism metadata to the raw telemetry payload."""
        # Create a copy so we do not mutate the original reading reference
        payload = reading.copy()
        
        # Determine location from asset_id for realism
        asset_id = payload.get("asset_id", "UNKNOWN_DEVICE")
        location_map = {
            "STP_HOSTEL_A": "Hostel Sector - Zone A",
            "STP_HOSTEL_B": "Hostel Sector - Zone B",
            "STP_CANTEEN": "Central Canteen Block",
            "STP_LAB_BLOCK": "Academic Labs Block"
        }
        
        payload["device_id"] = asset_id
        payload["location"] = location_map.get(asset_id, "Campus General")
        payload["device_type"] = "wastewater_monitor"
        
        # Remove scenario and internal tick if needed, though they are fine to keep for demo purposes.
        # Leaving them in makes it easier to trace anomalies on the backend.
        
        return payload
        
    def send_telemetry(self, reading: dict) -> bool:
        """
        Sends the specific telemetry reading to the API endpoint with 1 retry.
        Returns True if successful, False otherwise.
        """
        payload = self._enrich_payload(reading)
        
        attempt = 0
        while attempt <= self.max_retries:
            try:
                response = requests.post(
                    self.endpoint, 
                    json=payload, 
                    timeout=self.timeout
                )
                
                # Treat Any 2xx code as success
                if 200 <= response.status_code < 300:
                    return True
                else:
                    print(f"[WARN] {payload['device_id']} received HTTP {response.status_code} from endpoint.")
                    
            except requests.exceptions.RequestException as e:
                # Log the failure but don't crash
                # Only log on the final attempt to avoid terminal spam
                if attempt == self.max_retries:
                    print(f"[ERROR] {payload['device_id']} failed to reach endpoint ({self.endpoint}): {e}")
            
            attempt += 1
            if attempt <= self.max_retries:
                # Small exponential backoff for the retry
                time.sleep(1.0)
                
        return False
