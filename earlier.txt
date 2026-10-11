**Subject:** Re: TransportLah Spec - Proposed Implementation Plan & Commercial Terms

Hi Aveek,

Great going through the TransportLah specifications. It is a solid, very well-thought-out product proposal. The key differentiator is spot on: Singapore already has great route planners, but an engagement, gamified rewards, and sustainability platform built on top of LTA DataMall is where the real value lies.

I have attached our comprehensive **TransportLah — Technical Architecture & Implementation Plan (PDF)** to this email, which details our complete system design, LTA DataMall proxy caching, PostGIS spatial data models, confidence scoring equations, and cloud CI/CD pipelines.

Below is the executive summary of our architecture and proposed commercial terms:

---

### 1. Delivery & Cloud-Native Architecture Highlights
* **Mobile Client:** Built in **Flutter** (Dart) for a single, high-performance codebase delivering native 60fps UX across both iOS and Android without duplicated engineering.
* **Zero Local Bottlenecks (Cloud CI/CD):** 
  * All **iOS builds** compile directly in the cloud via **GitHub Actions macOS CI** into Apple TestFlight.
  * All **Android builds** compile and sign via cloud runners into Google Play Console.
* **LTA DataMall Integration & Caching:** Dedicated backend proxy to guard the `AccountKey`, with intelligent Redis caching for static stops/routes and on-demand polling for live bus arrivals and MRT crowd levels.
* **Lightweight Verification Engine (The Core IP):** A privacy-first confidence scoring engine (0–100 score). Instead of battery-draining continuous tracking, it evaluates stop proximity, service alignment, LTA arrival timestamp correlation, route corridor matching, and downstream alighting before crediting Green Points.
* **Gamification & Leaderboards:** Real-time Redis Sorted Sets for sub-5ms rankings (Global, Friends, School/Company, and Verified-only views), plus Green Points ledger and badge progression.
* **Admin & Campaign Portal:** A clean web dashboard (Next.js/Tailwind) for sponsors and admins to configure contests, upload banners, and review suspicious ride alerts.

---

### 2. Commercial Engagement Options & Advance Terms

#### Option A: Full Turnkey MVP Delivery (Recommended)
* **Scope:** End-to-end delivery of Flutter iOS & Android apps + Backend Microservices (LTA proxy, PostGIS, Redis) + Privacy-first Ride Verification Engine + Admin Web Portal + Store Deployments.
* **Timeline:** 8 Weeks (4 Sprints).
* **Total Project Fee:** **SGD 15,000** *(or INR 9,50,000)*
* **Payment Schedule:**
  1. **35% Advance upon Project Kickoff:** **SGD 5,250** *(locks architecture, cloud CI/CD pipelines, and Sprint 1 initiation)*
  2. **30% Milestone 2 Delivery:** **SGD 4,500** *(Backend proxy + PostGIS spatial schema + Flutter app with live arrivals & ride verification engine)*
  3. **20% Milestone 3 Delivery:** **SGD 3,000** *(Green Points gamification + Redis live leaderboards + Admin Campaign portal)*
  4. **15% Final Handover:** **SGD 2,250** *(End-to-end testing, TestFlight / Play Store deployment, and complete IP/repo transfer)*

---

#### Option B: Monthly CTO & Technical Leadership Retainer
* **Scope:** Architecture, core algorithmic verification engine, API pipelines, sprint direction, and bi-weekly demos.
* **Retainer Fee:** **SGD 4,000 / month** *(or INR 2,50,000 / month)*
* **Terms:** **100% advance at the beginning of each 30-day sprint cycle** (2-month minimum).

---

#### Option C: Core Backend & Verification Engine Only
* **Scope:** For if your internal team wants to build the mobile screens, I deliver the complete LTA proxy, spatial verification algorithms, Redis leaderboards, and REST/WebSocket API endpoints.
* **Total Fee:** **SGD 9,500** *(40% advance upon signing: SGD 3,800; 40% on API sandbox release; 20% on final handover)*.

---

*(Note: Third-party accounts such as Apple Developer Program $99/yr, Google Play $25, LTA DataMall API key, and AWS/GCP cloud hosting will be provisioned directly under your company credentials).*

Please review the attached PDF for the in-depth system diagrams and milestone deliverables. Let me know which engagement option works best for your timeline, Aveek, and we will share the bank details for the kickoff advance, lock down the repository, and begin Sprint 1 right away.

Best regards,  
Kunal

--  
**Kunal Das**  
Director & CTO @ MyFastx · AI-First Technology Leader  
WhatsApp/text: +91 86172 16163 · email preferred · no calls please  
isearch.xsolve@gmail.com
