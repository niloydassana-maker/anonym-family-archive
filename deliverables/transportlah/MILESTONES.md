# TransportLah Engineering Milestones & Acceptance Criteria

This document defines the milestone gates and verification criteria for the TransportLah pilot. Each milestone specifies an empirical acceptance gate.

---

### Milestone 1 (M1): Transit Telemetry Ingestion Pipeline
- Deliverable: Singapore transit bus arrival feed ingestion and multi-stop rate-limited proxy caching.
- ACCEPT: Proxy successfully processes transit arrival telemetry and validates incoming bus service data.

---

### Milestone 2 (M2): Database-Backed Corridor Verification & Spatial Indexing
- Deliverable: Spatial indexing with GiST geometry indices and corridor evaluation.
- ACCEPT: Spatial corridor query evaluates within tolerance with <=30.0s temporal drift and passes differential fuzz test battery.

---

### Milestone 3 (M3): Commuter App Initial TestFlight Client Build
- Deliverable: Native iOS TestFlight client build capturing background GPS pings and synchronizing with backend API.
- ACCEPT: iOS TestFlight build successfully deploys to Apple App Store Connect and installs on test device.
