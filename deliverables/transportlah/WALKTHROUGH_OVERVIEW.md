# TransportLah — Spatial Verification & LTA DataMall Testbench
**Prepared for:** Aveek Sengupta  
**Architecture Lead:** Kunal Das  

---

### Executive Summary
TransportLah evaluates validation of commuter bus journeys across Singapore's transit network. This local testbench demonstrates:
1. **LTA DataMall Proxying with In-Memory TTL Cache:** In-memory caching layer storing bus stop ETA and vehicle positions for a duration of 30 seconds [ASSUMPTION: cache TTL]. Operates in `LIVE_NETWORK` mode if a key is provided, or `OFFLINE_FIXTURE` mode for local testing.
2. **Geodesic Spatial Corridor Matching:** Haversine formula and PostGIS spatial schema (`schema_postgis.sql`) matching commuter smartphone GPS coordinates against vehicle locations.
3. **Ride Completion Verification:** Temporal and spatial threshold scoring requiring >= 75% [ASSUMPTION: minimum threshold] correlation within 100 meters [ASSUMPTION: spatial corridor width] and 30 seconds [ASSUMPTION: max temporal drift].

---

### Testbench Architecture
```
[ Commuter App ] 
       │ (GPS Pings)
       ▼
[ Spatial Verification Engine ] ◄── (Vehicle GPS & ETA) ── [ LTA DataMall Proxy ]
       │                                                          │
       ▼                                                          ▼
[ Trip Verification Result ]                                [ Singapore LTA API ]
```

---

### Test Vector Run Receipt
* **Test Node:** Orchard Station / Tangs (`BusStopCode: 09048`), Service `190` [TEST VECTOR]
* **Evaluated Pings:** 3 spatial segments along Orchard Road to Dhoby Ghaut [ASSUMPTION: sample route]
* **Verification Status:** Pass (confidence score: 100.0% [TEST VECTOR CALCULATION])
* **Average Spatial Deviation:** 26.21 meters [TEST VECTOR CALCULATION]
* **Temporal Drift Tolerance:** 30.0 seconds [ASSUMPTION]

---

### KNOWN LIMITATIONS (Disclosed from Unit Test Suite)
1. **Single-Ping Rides Rejected:** A commuter submitting only 1 ping is rejected (< 2 pings required).
2. **KNOWN LIMIT — 90m Pedestrian:** A pedestrian walking on a sidewalk parallel to a slow-moving bus at 90m distance passes verification because 90m is within the 100m corridor threshold [ASSUMPTION: 100m tolerance]. The engine cannot differentiate an adjacent pedestrian from an onboard passenger without accelerometer/sensor fusion.
3. **KNOWN LIMIT — Replay / Spoof:** Replaying exact public bus coordinates with matching timestamps (spoof) passes verification (100% score). Replay / spoof cannot be detected without hardware-backed cryptographic device attestation.

---

### Sprint 1 Delivery Plan
- **Sprint 1 (Days 1–10 [ESTIMATE]):** Deliver initial TestFlight iOS client build and transit ride verification integration.

