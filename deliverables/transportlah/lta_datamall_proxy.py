"""
TransportLah - Singapore LTA DataMall API Proxy & Rate-Limited Cache
Provides deterministic transit data caching and live LTA DataMall integration.

Modes:
- LIVE_NETWORK: Enabled when an authentic LTA DataMall AccountKey is configured.
- OFFLINE_FIXTURE: Pre-recorded Singapore transit vectors for deterministic testing without an API key.
"""

import time
import json
import os
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any

class LTADataMallProxy:
    BASE_URL = "https://datamall2.mytransport.sg/ltaodataservice/v3"

    # Known recorded Singapore transit test vectors
    RECORDED_FIXTURES = {
        "09048": {  # Orchard Stn / Tangs
            "190": {
                "Operator": "SMRT",
                "OriginCode": "44009",
                "DestinationCode": "03211",
                "NextBus": {
                    "EstimatedArrival": "2026-10-10T23:55:00+08:00",
                    "Latitude": 1.3048,
                    "Longitude": 103.8318,
                    "VisitNumber": "1",
                    "Load": "Seats Available",
                    "Type": "Double Deck"
                },
                "NextBus2": {
                    "EstimatedArrival": "2026-10-11T00:08:00+08:00",
                    "Latitude": 1.3210,
                    "Longitude": 103.8205,
                    "Load": "Standing Available",
                    "Type": "Single Deck"
                },
                "NextBus3": {
                    "EstimatedArrival": "2026-10-11T00:20:00+08:00",
                    "Latitude": 1.3325,
                    "Longitude": 103.8042,
                    "Load": "Seats Available",
                    "Type": "Double Deck"
                }
            }
        }
    }

    def __init__(self, api_key: Optional[str] = None, cache_ttl_sec: int = 30):
        # Look for key in parameter, environment, or key path
        env_key = os.environ.get("LTA_DATAMALL_KEY")
        vault_key_path = os.environ.get("LTA_KEY_PATH", "")
        vault_key = None
        if vault_key_path and os.path.exists(vault_key_path):
            try:
                with open(vault_key_path, "r", encoding="utf-8") as f:
                    vault_key = f.read().strip()
            except Exception:
                pass

        self.api_key = api_key or env_key or vault_key
        self.mode = "LIVE_NETWORK" if self.api_key else "OFFLINE_FIXTURE"
        self.cache_ttl = cache_ttl_sec
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _get_cached(self, key: str) -> Optional[Any]:
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["ts"] < self.cache_ttl:
                return entry["data"]
            del self._cache[key]
        return None

    def _set_cached(self, key: str, data: Any):
        self._cache[key] = {"data": data, "ts": time.time()}

    def get_bus_arrival(self, bus_stop_code: str, service_no: Optional[str] = None, bypass_cache: bool = False) -> Dict[str, Any]:
        """
        Fetch real-time bus arrival information for a given Singapore BusStopCode.
        """
        cache_key = f"arrival_{bus_stop_code}_{service_no or 'all'}"
        if not bypass_cache:
            cached = self._get_cached(cache_key)
            if cached:
                return cached

        # Mode 1: Live Network Call
        if self.mode == "LIVE_NETWORK":
            url = f"{self.BASE_URL}/BusArrival?BusStopCode={bus_stop_code}"
            if service_no:
                url += f"&ServiceNo={service_no}"
            
            headers = {"AccountKey": self.api_key, "accept": "application/json"}
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    data["_source"] = "LIVE_NETWORK"
                    self._set_cached(cache_key, data)
                    return data
            except urllib.error.HTTPError as e:
                return {
                    "error": True,
                    "status_code": e.code,
                    "message": f"LTA DataMall HTTP error: {e.reason}",
                    "_source": "LIVE_NETWORK_ERROR"
                }
            except Exception as e:
                return {
                    "error": True,
                    "message": f"Network error contacting LTA DataMall: {str(e)}",
                    "_source": "LIVE_NETWORK_ERROR"
                }

        # Mode 2: Offline Fixture (Clearly identified)
        fixture_stop = self.RECORDED_FIXTURES.get(bus_stop_code)
        if fixture_stop:
            if service_no and service_no in fixture_stop:
                srv = fixture_stop[service_no]
                data = {
                    "BusStopCode": bus_stop_code,
                    "Services": [{"ServiceNo": service_no, **srv}],
                    "_source": "OFFLINE_FIXTURE"
                }
            else:
                data = {
                    "BusStopCode": bus_stop_code,
                    "Services": [{"ServiceNo": k, **v} for k, v in fixture_stop.items()],
                    "_source": "OFFLINE_FIXTURE"
                }
            self._set_cached(cache_key, data)
            return data

        # Unknown bus stop code in offline fixture
        return {
            "BusStopCode": bus_stop_code,
            "Services": [],
            "error": True,
            "message": f"Bus stop code {bus_stop_code} not found in offline recorded fixtures. Live key required for unrecorded stops.",
            "_source": "OFFLINE_FIXTURE_NOT_FOUND"
        }

    def poll_trajectory(self, bus_stop_code: str, service_no: str, samples: int = 3) -> List[Dict[str, Any]]:
        """
        Poll and accumulate timestamped vehicle trajectory samples into a time series.
        In live network mode, polls successive arrival readings over time (bypassing TTL cache).
        In recorded fixture mode, extracts the sequence of incoming vehicle positions (NextBus, NextBus2, NextBus3)
        provided by the recorded LTA BusArrival service response.
        """
        trajectory_history: List[Dict[str, Any]] = []
        for _ in range(samples):
            arrival = self.get_bus_arrival(bus_stop_code, service_no, bypass_cache=True)
            if "Services" in arrival and arrival["Services"]:
                svc = arrival["Services"][0]
                if not self.api_key:
                    for key in ("NextBus", "NextBus2", "NextBus3"):
                        nb = svc.get(key, {})
                        if "Latitude" in nb and "Longitude" in nb and "EstimatedArrival" in nb:
                            trajectory_history.append({
                                "lat": float(nb["Latitude"]),
                                "lng": float(nb["Longitude"]),
                                "timestamp": str(nb["EstimatedArrival"])
                            })
                    break
                else:
                    nb = svc.get("NextBus", {})
                    if "Latitude" in nb and "Longitude" in nb and "EstimatedArrival" in nb:
                        trajectory_history.append({
                            "lat": float(nb["Latitude"]),
                            "lng": float(nb["Longitude"]),
                            "timestamp": str(nb["EstimatedArrival"])
                        })
        return trajectory_history[:samples]
