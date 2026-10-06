# TransportLah — Implementation Plan & Commercial Proposal (Updated with Advance Terms)
**Prepared for:** Aveek  
**Prepared by:** Kunal Das (Director & CTO @ MyFastx | AI-First Technology Leader)  
**Channel:** isearch.xsolve@gmail.com | WhatsApp/Text: +91 86172 16163 (Written lane preferred)  
**Date:** October 2026  
**Document Ref:** TL-PROP-2026-V2  

---

## 1. Executive Summary & Delivery Architecture

TransportLah is Singapore's green commute rewards and engagement platform:
> **"Ride green. Earn rewards. Climb the leaderboard."**

### Cloud-Native Build & Deployment Strategy (Zero Local Friction)
To ensure rapid, clean delivery across both iOS and Android without dependency on local hardware:
* **Cross-Platform Core:** Built in **Flutter** (Dart), yielding a single production codebase for iOS & Android.
* **Automated Cloud CI/CD:** 
  * **iOS:** Built via cloud macOS runners (GitHub Actions) targeting **Apple TestFlight** and App Store Connect automatically.
  * **Android:** Built and signed via Cloud CI, producing release `.aab` bundles for Google Play Console.
* **Backend & Verification Engine:** Dockerized microservices deployed on AWS (ECS Fargate + RDS PostgreSQL/PostGIS + ElastiCache Redis).

---

## 2. Technical Scope & Core Modules

### Module 1: LTA DataMall Gateway & Secure Caching Proxy
* Backend proxy shielding the LTA `AccountKey`.
* Smart Redis caching: static stops/routes (24h sync), live bus arrivals (on-demand stop query), MRT crowd & alerts (30s TTL).

### Module 2: Lightweight Ride Verification Engine (Core IP)
* Privacy-first 7-factor confidence scoring (0–100): Stop geofence, official service match, live arrival timestamp sync, corridor trajectory, speed bounds, corridor tolerance, and downstream alighting.
* Multi-tiered rewards (Tier 1 Basic -> Tier 2 Full Verified -> Tier 3 Contest Eligible).
* Zero long-term GPS retention (purged within 48–72h).

### Module 3: Fare-Smart Route Comparison
* Distance-based calculation using official PTC fare tables.
* Trade-off cards: Fastest vs. Cheapest vs. Least Crowded vs. Best Rewards.

### Module 4: Gamification, Streaks & Live Leaderboards
* Green Points ledger & Badges.
* Sub-5ms Redis Sorted Set leaderboards (Global, Weekly, Friends, School/Company).

### Module 5: Admin & Campaign Web Portal
* Next.js/Tailwind web portal for campaign managers and sponsors to configure contests, upload banners, and review fraud alerts.

---

## 3. Commercial Models & Advance Terms

### Option A: Fixed-Scope Turnkey MVP (Recommended)
* **Total Project Fee:** **SGD 15,000** *(or INR 9,50,000 equivalent)*
* **Timeline:** 8 Weeks (4 Sprints)
* **Milestone & Advance Payment Structure:**
  1. **35% Advance upon Contract Signing / Project Kickoff:** **SGD 5,250** *(covers architecture lock, cloud CI/CD pipelines, and Sprint 1 initiation)*
  2. **30% Milestone 2 Delivery:** **SGD 4,500** *(Working backend proxy + PostGIS schema + Flutter MVP with live arrivals & ride verification engine)*
  3. **20% Milestone 3 Delivery:** **SGD 3,000** *(Gamification engine + Live leaderboards + Admin Campaign portal)*
  4. **15% Final Acceptance & Handover:** **SGD 2,250** *(End-to-end security audits, TestFlight / Play Store deployment, and complete code repository transfer)*

---

### Option B: Monthly Technical Leadership & Core Engine Retainer
* Direct CTO-level ownership: Architecture, core verification algorithms, API pipelines, and sprint management.
* **Retainer Fee:** **SGD 4,000 / month** *(or INR 2,50,000 / month)*
* **Payment Term:** **100% advance at the beginning of each 30-day billing cycle**.
* **Initial Commitment:** 2 months minimum.

---

### Option C: Backend Core & Verification Engine Only
* Complete LTA proxy, PostGIS spatial pipeline, verification engine, Redis leaderboards, and REST/WebSocket API for Aveek's internal app team.
* **Total Fee:** **SGD 9,500**
* **Terms:** **40% Advance on signing (SGD 3,800)**, 40% on API sandbox release, 20% on final handover.

---

## 4. Infrastructure & Third-Party Accounts
* Developer accounts (Apple Developer Program $99/year, Google Play Console $25 one-time) and Cloud hosting (AWS/GCP, domain, LTA API key) are provisioned under Aveek's / TransportLah company credentials.
