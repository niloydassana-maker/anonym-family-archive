import subprocess
import os

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>TransportLah — Technical Architecture & Implementation Plan</title>
<style>
  @page {
    size: A4;
    margin: 18mm 16mm 18mm 16mm;
  }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1e293b;
    line-height: 1.5;
    font-size: 12.5px;
    background-color: #ffffff;
    margin: 0;
    padding: 0;
  }
  .header-cover {
    border-bottom: 3px solid #10b981;
    padding-bottom: 20px;
    margin-bottom: 22px;
  }
  .badge {
    background-color: #ecfdf5;
    color: #059669;
    padding: 4px 10px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    display: inline-block;
    border: 1px solid #a7f3d0;
  }
  h1 {
    font-size: 24px;
    color: #0f172a;
    margin: 10px 0 4px 0;
    letter-spacing: -0.02em;
  }
  .subtitle {
    font-size: 14px;
    color: #475569;
    font-weight: 400;
    margin-bottom: 16px;
  }
  .meta-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 11.5px;
  }
  .meta-item strong {
    color: #334155;
  }
  h2 {
    font-size: 16px;
    color: #0f172a;
    border-left: 4px solid #10b981;
    padding-left: 10px;
    margin-top: 24px;
    margin-bottom: 10px;
  }
  h3 {
    font-size: 13.5px;
    color: #1e293b;
    margin-top: 14px;
    margin-bottom: 6px;
  }
  p {
    margin: 0 0 8px 0;
    color: #334155;
  }
  ul, ol {
    margin: 0 0 10px 0;
    padding-left: 20px;
    color: #334155;
  }
  li {
    margin-bottom: 3px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0 16px 0;
    font-size: 11.5px;
  }
  th, td {
    padding: 7px 9px;
    text-align: left;
    border-bottom: 1px solid #e2e8f0;
  }
  th {
    background-color: #f1f5f9;
    color: #1e293b;
    font-weight: 600;
  }
  tr:nth-child(even) td {
    background-color: #f8fafc;
  }
  .card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 12px;
    margin-bottom: 12px;
  }
  .card-highlight {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 6px;
    padding: 12px;
    margin-bottom: 12px;
  }
  .code-block {
    background-color: #0f172a;
    color: #f8fafc;
    padding: 10px 12px;
    border-radius: 6px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 10px;
    line-height: 1.4;
    margin: 8px 0 14px 0;
  }
  .page-break {
    page-break-before: always;
  }
</style>
</head>
<body>

<div class="header-cover">
  <span class="badge">Technical Architecture & Implementation Blueprint</span>
  <h1>TransportLah — System Architecture & Delivery Plan</h1>
  <div class="subtitle">A gamified, privacy-first green commute rewards platform for Singapore</div>
  
  <div class="meta-grid">
    <div class="meta-item"><strong>Client / Stakeholder:</strong> Aveek Sengupta</div>
    <div class="meta-item"><strong>Document Ref:</strong> TL-ARCH-2026-V2</div>
    <div class="meta-item"><strong>Prepared By:</strong> Kunal Das (Director & CTO @ MyFastx)</div>
    <div class="meta-item"><strong>Date:</strong> October 2026</div>
    <div class="meta-item"><strong>Email:</strong> isearch.xsolve@gmail.com</div>
    <div class="meta-item"><strong>WhatsApp / Text:</strong> +91 86172 16163 (Written lane preferred)</div>
  </div>
</div>

<h2>1. Executive Summary & Market Differentiator</h2>
<p>
Singapore has mature transport utilities (Citymapper, MyTransport.SG, SG BusLeh, and SimplyGo). 
TransportLah does not seek to duplicate basic journey navigation. Instead, it leverages real-time LTA DataMall 
transit feeds to establish Singapore’s first <strong>verified green mobility reward and challenge platform</strong>:
</p>
<div class="card-highlight">
  <strong>The Core Product Loop:</strong><br>
  <strong>Plan Ride</strong> &rarr; <strong>Verify Ride (Privacy-First)</strong> &rarr; <strong>Earn Green Points</strong> &rarr; <strong>Join Sponsor Contests</strong> &rarr; <strong>Climb Leaderboard</strong> &rarr; <strong>Redeem Impact Rewards</strong>
</div>

<h2>2. Cloud-Native Build & Hardware Architecture (Zero Local Overhead)</h2>
<p>
To ensure absolute reliability, rapid development velocity, and complete independence from local development hardware:
</p>
<ul>
  <li><strong>Cross-Platform Mobile Core (Flutter / Dart):</strong> A single unified codebase delivering native 60fps performance across both iOS and Android. Zero duplication of business logic or UI states.</li>
  <li><strong>Cloud macOS CI/CD for iOS (GitHub Actions):</strong> Apple requires macOS/Xcode for iOS compilation. We utilize cloud-hosted macOS virtual runners on GitHub Actions to compile <code>.ipa</code> builds and deploy automatically to <strong>Apple TestFlight</strong>.</li>
  <li><strong>Cloud Linux CI/CD for Android:</strong> Automated builds compile and sign release <code>.aab</code> bundles for direct release to Google Play Console.</li>
  <li><strong>Cloud Containerized Backend:</strong> Microservices containerized in Docker, running on scalable AWS / GCP managed infrastructure (ECS Fargate + RDS PostgreSQL/PostGIS + ElastiCache Redis).</li>
</ul>

<h2>3. End-to-End System Architecture</h2>
<div class="code-block">
+-------------------------------------------------------------------------+
|                  TransportLah Mobile Client (Flutter)                    |
|       [Home Dashboard] [Journey Planner] [Live Bus/MRT Arrivals]        |
|       [Active Ride Verification] [Rewards Wallet] [Leaderboards]        |
+------------------------------------+------------------------------------+
                                     | HTTPS / WSS
                                     v
+-------------------------------------------------------------------------+
|                    API Gateway & Authentication Service                 |
|             • JWT & OAuth2 (Apple / Google / Mobile OTP)                |
|             • Rate Limiting, SSL Termination & Request Validation       |
+------------------------------------+------------------------------------+
                                     |
    +--------------------------------+--------------------------------+
    |                                |                                |
    v                                v                                v
+----------------------+  +----------------------+  +----------------------+
|  LTA DataMall Proxy  |  |   Ride Verification  |  | Fare-Smart & Journey |
|  • AccountKey Guard  |  |   Engine (Core IP)   |  |   Optimisation       |
|  • Redis In-Memory   |  |  • Geofence checking |  |  • PTC distance fare |
|    Cache (Stops/ETA) |  |  • Route corridor    |  |  • Transfer rules    |
|  • Crowd & Disrupt   |  |  • 7-Factor Score    |  |  • Trade-off matrix  |
+----------------------+  +----------------------+  +----------------------+
    |                                |                                |
    +--------------------------------+--------------------------------+
                                     |
    +--------------------------------+--------------------------------+
    |                                |                                |
    v                                v                                v
+----------------------+  +----------------------+  +----------------------+
| Gamification Engine  |  |  Leaderboard Engine  |  | Admin & Sponsor Web  |
| • Green Points ledger|  | • Redis Sorted Sets  |  | • Next.js Dashboard  |
| • Streaks & Badges   |  | • Sub-5ms rankings   |  | • Campaign Builder   |
| • Level progression  |  | • Team / School sets |  | • Fraud Review Queue |
+----------------------+  +----------------------+  +----------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                              Data Layer                                 |
|   • PostgreSQL 16 + PostGIS: Spatial stop coordinates, routes, users   |
|   • Redis 7: Active ride ephemeral states, fast caches, leaderboards    |
|   • AWS S3: Campaign banners, sponsor creatives, report exports         |
+-------------------------------------------------------------------------+
</div>

<div class="page-break"></div>

<h2>4. Lightweight Ride Verification Engine (The Core IP)</h2>
<p>
Unlike battery-draining navigation apps that constantly track users, TransportLah implements a 
<strong>privacy-first confidence scoring algorithm</strong>. Location sampling occurs only during active rides, 
and raw traces are permanently purged within 48–72 hours.
</p>

<h3>Multi-Factor Confidence Scoring Matrix (Total: 100 Points)</h3>
<table>
  <thead>
    <tr>
      <th>Signal</th>
      <th>Verification Metric & Logic</th>
      <th>Weight</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>1. Stop Proximity</strong></td>
      <td>Boarding coordinates fall within 50m of an official LTA bus stop or MRT station (PostGIS <code>ST_DWithin</code>).</td>
      <td>15 pts</td>
    </tr>
    <tr>
      <td><strong>2. Service Match</strong></td>
      <td>User's selected bus service officially serves the boarding stop.</td>
      <td>10 pts</td>
    </tr>
    <tr>
      <td><strong>3. Live Arrival Correlation</strong></td>
      <td>Cross-referenced with LTA live arrival API; confirms vehicle arrived within &plusmn;3 min of check-in.</td>
      <td>20 pts</td>
    </tr>
    <tr>
      <td><strong>4. Route Corridor Following</strong></td>
      <td>User trajectory tracks official stop sequence (Stop N &rarr; N+1 &rarr; N+2).</td>
      <td>25 pts</td>
    </tr>
    <tr>
      <td><strong>5. Kinematic Plausibility</strong></td>
      <td>Speed profile matches public transit dynamics (12–65 km/h; rejects walking or private car speeds).</td>
      <td>10 pts</td>
    </tr>
    <tr>
      <td><strong>6. Corridor Tolerance</strong></td>
      <td>User coordinates remain within a 150m buffer of the route line geometry.</td>
      <td>10 pts</td>
    </tr>
    <tr>
      <td><strong>7. Alighting Verification</strong></td>
      <td>Ride ends in proximity to a downstream official stop along the same line.</td>
      <td>10 pts</td>
    </tr>
  </tbody>
</table>

<h3>Verification Tiers & Point Allocations</h3>
<table>
  <thead>
    <tr>
      <th>Confidence Score</th>
      <th>Verification Status</th>
      <th>Points & Contest Eligibility</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>80 – 100</strong></td>
      <td><span style="color:#059669; font-weight:bold;">Verified Ride</span></td>
      <td>100% Green Points awarded + Fully eligible for public/sponsor contests.</td>
    </tr>
    <tr>
      <td><strong>60 – 79</strong></td>
      <td><span style="color:#d97706; font-weight:bold;">Probable Ride</span></td>
      <td>Partial points awarded (50%); personal streak preserved; not contest eligible.</td>
    </tr>
    <tr>
      <td><strong>40 – 59</strong></td>
      <td><span style="color:#64748b;">Low Confidence</span></td>
      <td>Logged in personal commuter statistics only; 0 Green Points.</td>
    </tr>
    <tr>
      <td><strong>&lt; 40</strong></td>
      <td><span style="color:#dc2626; font-weight:bold;">Rejected / Flagged</span></td>
      <td>Zero points; repeated triggers routed to Admin Fraud Review queue.</td>
    </tr>
  </tbody>
</table>

<h2>5. Database & Spatial Architecture (PostGIS + Redis)</h2>
<div class="card">
  <strong>Key Spatial & Ephemeral Models:</strong>
  <ul>
    <li><code>stops</code> (id, code, name, geom GEOMETRY(Point, 4326), mode) &mdash; Indexed with <code>GIST(geom)</code> for sub-millisecond geofence queries.</li>
    <li><code>route_corridors</code> (service_no, direction, path GEOMETRY(LineString, 4326)) &mdash; Route corridor matching and buffer validation.</li>
    <li><code>rides</code> (id, user_id, mode, service_no, start_stop, end_stop, start_time, end_time, confidence_score, status).</li>
    <li><code>leaderboard_cache</code> (Redis Sorted Sets: <code>ZADD leaderboard:global:2026-w40 &lt;points&gt; &lt;user_id&gt;</code>) &mdash; Instant sub-5ms ranking queries via <code>ZREVRANGE</code>.</li>
  </ul>
</div>

<div class="page-break"></div>

<h2>6. 8-Week MVP Implementation Roadmap</h2>
<table>
  <thead>
    <tr>
      <th>Sprint / Phase</th>
      <th>Duration</th>
      <th>Key Deliverables</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Sprint 1: Architecture & Data Ingestion</strong></td>
      <td>Weeks 1 &ndash; 2</td>
      <td>
        &bull; PostgreSQL + PostGIS schema setup & Redis cache layer.<br>
        &bull; LTA DataMall proxy service (Stops, Routes, Live Arrivals, Alerts).<br>
        &bull; User Auth (Apple & Google Sign-In) & Cloud CI/CD repository setup.
      </td>
    </tr>
    <tr>
      <td><strong>Sprint 2: Mobile Core & Verification Engine</strong></td>
      <td>Weeks 3 &ndash; 4</td>
      <td>
        &bull; Flutter UI: Home Dashboard, Route Planner, Live Bus Screen with crowd badges.<br>
        &bull; Ride Verification Engine implementation (7-Factor Scoring).<br>
        &bull; Basic Fare-Smart distance fare calculator & transfer warnings.
      </td>
    </tr>
    <tr>
      <td><strong>Sprint 3: Gamification & Admin Portal</strong></td>
      <td>Weeks 5 &ndash; 6</td>
      <td>
        &bull; Green Points ledger, streaks, badges, and user level progression.<br>
        &bull; Redis-backed live leaderboards (Global, Weekly, Friends).<br>
        &bull; Next.js Admin Portal: Contest builder, banner manager, fraud review.
      </td>
    </tr>
    <tr>
      <td><strong>Sprint 4: Hardening & App Store Deployment</strong></td>
      <td>Weeks 7 &ndash; 8</td>
      <td>
        &bull; Anti-spoofing tests, geofence tuning, load testing.<br>
        &bull; TestFlight (iOS) and Internal Testing (Google Play) builds.<br>
        &bull; Production launch handover & complete documentation.
      </td>
    </tr>
  </tbody>
</table>

<h2>7. Commercial Models & Advance Terms</h2>

<div class="card-highlight">
  <h3>Option A: Full Turnkey MVP Delivery (Recommended)</h3>
  <p><strong>Total Project Investment:</strong> <strong>SGD 15,000</strong> <em>(or INR 9,50,000)</em></p>
  <p><strong>Milestone & Advance Payment Structure:</strong></p>
  <ol>
    <li><strong>35% Advance upon Project Kickoff:</strong> <strong>SGD 5,250</strong> <em>(~INR 3,32,000)</em> &mdash; Paid upfront to initiate architecture lock, CI/CD pipeline setup, and Sprint 1.</li>
    <li><strong>30% Milestone 2 Delivery:</strong> <strong>SGD 4,500</strong> <em>(~INR 2,85,000)</em> &mdash; Delivered working backend proxy + PostGIS + Flutter MVP with live arrivals & ride verification.</li>
    <li><strong>20% Milestone 3 Delivery:</strong> <strong>SGD 3,000</strong> <em>(~INR 1,90,000)</em> &mdash; Delivered Gamification engine + Redis leaderboards + Admin Portal.</li>
    <li><strong>15% Final Handover:</strong> <strong>SGD 2,250</strong> <em>(~INR 1,42,000)</em> &mdash; App Store & Play Store deployment, complete IP & repository handover.</li>
  </ol>
</div>

<div class="card">
  <h3>Option B: Monthly CTO & Technical Leadership Retainer</h3>
  <p><strong>Retainer Fee:</strong> <strong>SGD 4,000 / month</strong> <em>(~INR 2,50,000 / month)</em></p>
  <p><strong>Terms:</strong> 100% advance at the beginning of each 30-day billing cycle (2-month minimum commitment).</p>
</div>

<div class="card">
  <h3>Option C: Core Backend & Verification Engine Only</h3>
  <p><strong>Total Investment:</strong> <strong>SGD 9,500</strong> <em>(40% advance upon signing: SGD 3,800; 40% on API sandbox release; 20% on final handover)</em>.</p>
</div>

<p style="font-size:11px; color:#64748b; margin-top:16px;">
<em>Note: Third-party infrastructure costs (Apple Developer Program $99/yr, Google Play $25, AWS/GCP hosting, domain, and official LTA API credentials) are provisioned directly under Aveek's / TransportLah's corporate entity.</em>
</p>

</body>
</html>
"""

html_path = r"D:\anonym\TransportLah_Implementation_Plan.html"
pdf_path = r"D:\anonym\TransportLah_Implementation_Plan.pdf"

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
cmd = [
    chrome_exe,
    "--headless=new",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={pdf_path}",
    html_path
]

res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
if os.path.exists(pdf_path):
    print(f"PDF regenerated: {pdf_path} ({os.path.getsize(pdf_path)} bytes)")
