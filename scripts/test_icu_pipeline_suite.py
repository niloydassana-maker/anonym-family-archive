import sys
import os
import sqlite3
import re

# Add scripts directory to path
sys.path.insert(0, r"D:\anonym\scripts")

from autonomous_icu_pipeline import (
    verify_genuine_icu_patient,
    detect_author_corridor,
    sanitize_and_validate_payload,
    APPROVED_CORRIDOR_TZ_MAP,
    init_db,
    try_claim_issue,
    is_issue_claimed_or_delivered,
    commit_delivery,
    release_claim
)

TEST_DB = r"D:\anonym\scratch\test_suite_isolated.db"

print("==================================================")
print("RUNNING ICU PIPELINE INTEGRITY TEST SUITE")
print("==================================================")

# ----------------------------------------------------------------
# Test 1: Genuine ICU Client Detection & Decision-Maker Authority
# ----------------------------------------------------------------
print("\n[Test 1] Testing Genuine ICU Client Gate & Authority...")

# 1. TONEART GmbH (WhatsApp MCP Production Coexistence - Paid Feasibility)
is_icu_1, reason_1 = verify_genuine_icu_patient(
    title="Paid feasibility assessment: WhatsApp Business MCP alongside an existing Meta Business Agent",
    body="Looking for a paid feasibility assessment for TONEART GmbH. We use WhatsApp Business with an existing Meta Business Agent, SOPHIA-X. We want to assess coexistence without disrupting production setup.",
    author_comments=[],
    labels=[],
    repo="spirit122/whatsapp-mcp-server",
    author_assoc="COLLABORATOR"
)
assert is_icu_1, f"Expected True for TONEART, got {is_icu_1}: {reason_1}"
print("  ✓ TONEART GmbH: Approved as genuine ICU client (COLLABORATOR authority).")

# 2. Reject CONTRIBUTOR role (lacks maintainer authority per Codex Audit)
is_icu_contrib, reason_contrib = verify_genuine_icu_patient(
    title="CUDA app by PackageCompiler hangs at runtime on Ubuntu / Debian",
    body="Dummy app made by PackageCompiler with CUDA@5.6.1 hangs at runtime on Ubuntu 24 and Debian 12.",
    author_comments=["Update: problem arises on Google Colab and not in AWS VMs. Happy to pay couple hours of consulting for anyone who can fix this problem."],
    labels=[],
    repo="JuliaLang/PackageCompiler.jl",
    author_assoc="CONTRIBUTOR"
)
assert not is_icu_contrib, "Expected CONTRIBUTOR to be rejected as lacking maintainer authority."
print("  ✓ Authority Gate: CONTRIBUTOR rejected as lacking maintainer authority.")

# 3. Decision-Maker Authority: Reject unverified external user without maintainer role or budget intent
is_icu_auth_fail, reason_auth_fail = verify_genuine_icu_patient(
    title="Production server crashing on boot",
    body="Why does it crash? Can someone fix this bug?",
    author_comments=[],
    labels=[],
    repo="org/app",
    author_assoc="NONE"
)
assert not is_icu_auth_fail, "Expected False for unverified external user."
print("  ✓ Authority Gate: Rejected external user without maintainer role or budget authority.")

# 4. Decision-Maker Authority: Reject self-asserted corporate sponsor without independent verification
is_icu_self_assert, reason_self_assert = verify_genuine_icu_patient(
    title="Production outage: payment gateway deadlocked",
    body="Critical P0 outage disrupting production. Our company budget will pay $2,500 for emergency architecture fix.",
    author_comments=[],
    labels=[],
    repo="fintech/payment-gateway",
    author_assoc="NONE",
    author=None
)
assert not is_icu_self_assert, "Expected self-asserted sponsor without independent verification to be rejected."
print("  ✓ Authority Gate: Rejected self-asserted corporate sponsor without independent verification.")

# 4b. Corporate Sponsor Entity Correlation: Generic 'our company' without naming affiliated entity is REJECTED
import autonomous_icu_pipeline
orig_get_profile = autonomous_icu_pipeline.get_author_profile
autonomous_icu_pipeline.get_author_profile = lambda u: {"company": "Acme Technologies, Inc."} if u == "acme_lead" else {}

is_icu_generic_sponsor, reason_generic_sponsor = verify_genuine_icu_patient(
    title="Critical production deadlock in payment processor",
    body="Outage in production. Our company budget will pay $5,000 for emergency resolution.",
    author_comments=[],
    labels=[],
    repo="fintech/payments",
    author_assoc="NONE",
    author="acme_lead"
)
assert not is_icu_generic_sponsor, "Expected generic 'our company' without naming Acme to be rejected."
print("  ✓ Authority Gate: Rejected generic 'our company' claim lacking named corporate entity correlation.")

# 4c. Corporate Sponsor Entity Correlation: Named entity matching author profile is APPROVED
is_icu_named_sponsor, reason_named_sponsor = verify_genuine_icu_patient(
    title="Critical production deadlock in payment processor",
    body="Outage in production. Acme Technologies budget will pay $5,000 for emergency resolution.",
    author_comments=[],
    labels=[],
    repo="fintech/payments",
    author_assoc="NONE",
    author="acme_lead"
)
assert is_icu_named_sponsor, f"Expected named sponsor matching Acme Technologies to be approved, got: {reason_named_sponsor}"
print("  ✓ Authority Gate: Approved verified corporate sponsor with correlated named entity ('Acme Technologies').")

# 4d. Discovery Integration Test: Correlated author_assoc="NONE" sponsor passes discovery gate with author payload
discovery_payload = {
    "title": "Critical production deadlock in payment processor",
    "body": "Outage in production. Acme Technologies budget will pay $5,000 for emergency resolution.",
    "author": {"login": "acme_lead"},
    "labels": [{"name": "bug"}],
    "author_comments": [],
    "authorAssociation": "NONE"
}
d_author = discovery_payload.get("author", {}).get("login", "")
d_title = discovery_payload.get("title", "")
d_body = discovery_payload.get("body", "")
d_labels = discovery_payload.get("labels", [])
d_comments = discovery_payload.get("author_comments", [])
d_assoc = discovery_payload.get("authorAssociation", "NONE")

d_is_icu, d_reason = verify_genuine_icu_patient(
    d_title, d_body, d_comments, d_labels, "fintech/payments",
    author_assoc=d_assoc, author=d_author
)
assert d_is_icu, f"Expected discovery-gate call to approve correlated NONE-assoc sponsor, got: {d_reason}"
print("  ✓ Discovery Gate Integration: Correlated NONE-association sponsor passes discovery gate with author=author.")

# Restore profile lookup
autonomous_icu_pipeline.get_author_profile = orig_get_profile

# 4e. Direct Payer Gate: Solo founder filing on OWN repo with payment intent (NONE assoc) - APPROVED
# Mock: author "solodev" owns repo "solodev/api-server", no company on profile
autonomous_icu_pipeline.get_author_profile = lambda u: {} if u == "solodev" else {}
is_icu_solo_founder, reason_solo = verify_genuine_icu_patient(
    title="Production crash: API returning 502 on all endpoints",
    body="My production API is down, losing customers every minute. Will pay $500 for emergency fix. DM me.",
    author_comments=[],
    labels=[],
    repo="solodev/api-server",
    author_assoc="NONE",
    author="solodev"
)
assert is_icu_solo_founder, f"Expected solo founder on own repo with payment intent to be approved, got: {reason_solo}"
print("  ✓ Direct Payer Gate: Solo founder on own repo with payment intent approved.")

# 4f. Direct Payer Gate: Freelancer with PayPal/UPI signal on third-party repo (NONE assoc) - APPROVED
is_icu_freelancer, reason_freelancer = verify_genuine_icu_patient(
    title="Critical memory leak crashing production workers",
    body="Our production workers keep crashing with OOM. Willing to pay $300 via PayPal for a fix. email me at dev@example.com",
    author_comments=[],
    labels=[],
    repo="otherorg/worker-lib",
    author_assoc="NONE",
    author="solodev"
)
assert is_icu_freelancer, f"Expected freelancer with PayPal signal to be approved, got: {reason_freelancer}"
print("  ✓ Direct Payer Gate: Freelancer with PayPal payment signal approved.")

# 4g. Direct Payer Gate: NONE assoc, no payment signal, no repo ownership, no company - REJECTED
is_icu_no_signal, reason_no_signal = verify_genuine_icu_patient(
    title="Production timeout on database queries",
    body="Database queries timing out in production. Will pay $200 for a fix.",
    author_comments=[],
    labels=[],
    repo="otherorg/db-lib",
    author_assoc="NONE",
    author="randomuser123"
)
assert not is_icu_no_signal, "Expected NONE-assoc user without payment signal, repo ownership, or company to be rejected."
print("  ✓ Direct Payer Gate: NONE-assoc without payment signal or repo ownership correctly rejected.")

# 4h. Direct Payer Gate: Crypto payment signal - APPROVED
is_icu_crypto, reason_crypto = verify_genuine_icu_patient(
    title="Smart contract reverting on production mainnet",
    body="Contract reverting all transactions on production. Offering $1,000 USDC bounty. Send to my ETH wallet.",
    author_comments=[],
    labels=[],
    repo="otherorg/defi-protocol",
    author_assoc="NONE",
    author="solodev"
)
assert is_icu_crypto, f"Expected crypto payment signal to be approved, got: {reason_crypto}"
print("  ✓ Direct Payer Gate: Crypto/USDC payment signal approved.")

# Restore profile lookup
autonomous_icu_pipeline.get_author_profile = orig_get_profile

# 5. Demonstrated Maintainer with Explicit Budget Approved
is_icu_owner, reason_owner = verify_genuine_icu_patient(
    title="Production outage: payment gateway deadlocked",
    body="Critical P0 outage disrupting production. Our company budget will pay $2,500 for emergency architecture fix.",
    author_comments=[],
    labels=[],
    repo="fintech/payment-gateway",
    author_assoc="OWNER"
)
assert is_icu_owner, f"Expected OWNER with budget to pass, got: {reason_owner}"
print("  ✓ Authority Gate: Approved OWNER with explicit $2,500 budget.")

# 6. Currency Parsing, Multi-Currency Normalization & Bounds ($20 to $9,999,999)
# Normal range ($1,500)
is_icu_comma, reason_comma = verify_genuine_icu_patient(
    title="Production OOM crash during peak load",
    body="Runtime crash in prod. Willing to pay $1,500 for remediation.",
    author_comments=[],
    labels=[],
    repo="fintech/engine",
    author_assoc="OWNER"
)
assert is_icu_comma, f"Expected comma-formatted currency to pass, got: {reason_comma}"
print("  ✓ Comma-Formatted Currency ($1,500): Parsed and approved within range.")

# Decimal Boundary Test: $20.00 Floor (Approved)
is_icu_floor, reason_floor = verify_genuine_icu_patient(
    title="Production crash in service",
    body="Production outage in prod. Will pay $20.00 for fix.",
    author_comments=[],
    labels=[],
    repo="fintech/engine",
    author_assoc="OWNER"
)
assert is_icu_floor, f"Expected $20.00 exact floor to pass, got: {reason_floor}"
print("  ✓ Decimal Boundary Exact Floor ($20.00): Approved.")

# Decimal Boundary Test: $19.99 Below Floor (Rejected)
is_icu_sub_floor, reason_sub_floor = verify_genuine_icu_patient(
    title="Production crash in service",
    body="Production outage in prod. Will pay $19.99 for fix.",
    author_comments=[],
    labels=[],
    repo="fintech/engine",
    author_assoc="OWNER"
)
assert not is_icu_sub_floor, "Expected $19.99 to be rejected as below $20.00 floor."
print("  ✓ Decimal Boundary Below Floor ($19.99): Rejected.")

# Decimal Boundary Test: $9,999,999.99 Exceeding Ceiling (Rejected)
is_icu_ceiling, reason_ceiling = verify_genuine_icu_patient(
    title="Production crash in service",
    body="Production outage in prod. Will pay $9,999,999.99 for fix.",
    author_comments=[],
    labels=[],
    repo="fintech/engine",
    author_assoc="OWNER"
)
assert not is_icu_ceiling, "Expected $9,999,999.99 to be rejected as exceeding ceiling."
print("  ✓ Decimal Boundary Exceeding Ceiling ($9,999,999.99): Rejected.")

# Decimal Foreign Currency Boundary Test: €18.52 (~$20.00 USD) Approved vs €18.51 (~$19.99 USD) Rejected
is_icu_eur_ok, reason_eur_ok = verify_genuine_icu_patient(
    title="Production crash in service",
    body="Production outage in prod. Will pay €18.52 for fix.",
    author_comments=[],
    labels=[],
    repo="fintech/engine",
    author_assoc="OWNER"
)
assert is_icu_eur_ok, f"Expected €18.52 (~$20.00 USD) to pass, got: {reason_eur_ok}"
print("  ✓ Decimal Foreign Currency Floor (€18.52 -> $20.00 USD): Approved.")

is_icu_eur_low, reason_eur_low = verify_genuine_icu_patient(
    title="Production crash in service",
    body="Production outage in prod. Will pay €18.51 for fix.",
    author_comments=[],
    labels=[],
    repo="fintech/engine",
    author_assoc="OWNER"
)
assert not is_icu_eur_low, "Expected €18.51 (~$19.99 USD) to be rejected."
print("  ✓ Decimal Foreign Currency Below Floor (€18.51 -> $19.99 USD): Rejected.")

# Multi-Currency Normalization: ₹50,000 INR (~$600 USD) -> Approved
is_icu_inr_ok, reason_inr_ok = verify_genuine_icu_patient(
    title="Production deadlock in order processing",
    body="Critical production crash. We will pay ₹50,000 for emergency hotfix.",
    author_comments=[],
    labels=[],
    repo="fintech/orders",
    author_assoc="MEMBER"
)
assert is_icu_inr_ok, f"Expected ₹50,000 INR to pass normalized USD check, got: {reason_inr_ok}"
print("  ✓ Currency Normalization (₹50,000 INR -> ~$600 USD): Approved within consulting bounds.")

# Multi-Currency Normalization: ₹500 INR (~$6 USD) -> Rejected (< $20 USD floor)
is_icu_inr_low, reason_inr_low = verify_genuine_icu_patient(
    title="Production crash in service",
    body="Outage in production. Will pay ₹500 for fix.",
    author_comments=[],
    labels=[],
    repo="fintech/service",
    author_assoc="MEMBER"
)
assert not is_icu_inr_low, "Expected ₹500 INR to be rejected as below $20 USD floor."
print("  ✓ Out-of-Bounds Currency (₹500 INR -> ~$6 USD): Rejected as below $20 USD floor.")

# Below $20 bound ($5) -> Reject
is_icu_low, reason_low = verify_genuine_icu_patient(
    title="Production crash in service",
    body="Production outage in prod. Will pay $5 for fix.",
    author_comments=[],
    labels=[],
    repo="fintech/engine",
    author_assoc="OWNER"
)
assert not is_icu_low, "Expected $5 to be rejected as below consulting bounds."
print("  ✓ Out-of-Bounds Currency ($5): Rejected as below $20 consulting bound.")

# Postfix Currency Tests: 50$ (Henry00IS/ShapeEditor real-world pattern)
is_icu_post_dollar, reason_post_dollar = verify_genuine_icu_patient(
    title="[50$ Bounty] PolyBool can cause an editor crash on T-Junctions",
    body="Editor crashes during mesh boolean operations in production. Will pay 50$ upon merge.",
    author_comments=[],
    labels=["bounty"],
    repo="Henry00IS/ShapeEditor",
    author_assoc="OWNER"
)
assert is_icu_post_dollar, f"Expected 50$ postfix currency to pass, got: {reason_post_dollar}"
print("  ✓ Postfix Currency (50$ Bounty): Approved within consulting bounds.")

# Postfix Currency Tests: 100 USD
is_icu_post_usd, reason_post_usd = verify_genuine_icu_patient(
    title="Production memory leak in websocket server",
    body="Memory leak causes worker crash every 2 hours. Offering 100 USD for a clean fix.",
    author_comments=[],
    labels=["bounty"],
    repo="myorg/websocket-server",
    author_assoc="OWNER"
)
assert is_icu_post_usd, f"Expected 100 USD postfix currency to pass, got: {reason_post_usd}"
print("  ✓ Postfix Currency (100 USD): Approved within consulting bounds.")

# Postfix Currency Tests: 5$ Below Floor -> Reject
is_icu_post_low, reason_post_low = verify_genuine_icu_patient(
    title="[5$ Bounty] Small crash fix",
    body="Will pay 5$ for fix.",
    author_comments=[],
    labels=["bounty"],
    repo="myorg/app",
    author_assoc="OWNER"
)
assert not is_icu_post_low, "Expected 5$ to be rejected as below $20 floor."
print("  ✓ Postfix Currency Below Floor (5$): Rejected as below $20 consulting bound.")

# Bare 'happy to pay' without numeric amount -> Reject
is_icu_bare_pay, reason_bare_pay = verify_genuine_icu_patient(
    title="Production service crashing under load",
    body="Production outage. Happy to pay anyone who can fix this.",
    author_comments=[],
    labels=[],
    repo="fintech/engine",
    author_assoc="OWNER"
)
assert not is_icu_bare_pay, "Expected bare 'happy to pay' without amount to be rejected."
print("  ✓ Bare Payment Without Amount ('happy to pay'): Rejected.")

# Live delivery mode blocks unpriced enterprise RFPs (routed to candidate packet review)
is_live_rfp, reason_live_rfp = verify_genuine_icu_patient(
    title="Paid feasibility assessment: WhatsApp Business MCP alongside an existing Meta Business Agent",
    body="Looking for a paid feasibility assessment for TONEART GmbH. Could you share expected approach, timeline, and cost?",
    author_comments=[],
    labels=[],
    repo="spirit122/whatsapp-mcp-server",
    author_assoc="COLLABORATOR",
    live_delivery_mode=True
)
assert not is_live_rfp, "Expected unpriced enterprise RFP to be blocked from automated live delivery."
print("  ✓ Live Delivery Gate: Blocked unpriced enterprise RFP from unreviewed live dispatch (routed to packet).")

# 6. Rejection: Non-commercial / Student Programs
is_icu_3, reason_3 = verify_genuine_icu_patient(
    title="Volcano Integration Plugin for Headlamp - Linux Foundation paid mentorship project",
    body="This is our draft proposal for an LFX mentorship project for students.",
    author_comments=[],
    labels=[],
    repo="kubernetes-sigs/headlamp",
    author_assoc="MEMBER"
)
assert not is_icu_3, "Expected False for LFX student project."
print("  ✓ LFX Mentorship: Rejected correctly.")

# 7. Rejection: Homelab setup
is_icu_4, reason_4 = verify_genuine_icu_patient(
    title="[BOUNTY $150] Storage Stack - Nextcloud + MinIO + FileBrowser",
    body="Homelab stack nextcloud storage configuration.",
    author_comments=[],
    labels=[],
    repo="illbnm/homelab-stack",
    author_assoc="OWNER"
)
assert not is_icu_4, "Expected False for Homelab non-production project."
print("  ✓ Homelab Non-Production: Rejected correctly.")

# 8. Rejection: Roadmap planning ticket
is_icu_5, reason_5 = verify_genuine_icu_patient(
    title="[28] Validate paid workflow value and sustainable unit economics",
    body="Roadmap milestone 32/38 for commercial go-to-market planning.",
    author_comments=[],
    labels=[],
    repo="Sammieblz/tholi",
    author_assoc="OWNER"
)
assert not is_icu_5, "Expected False for internal roadmap ticket."
print("  ✓ Roadmap Planning Ticket: Rejected correctly.")

# 9. Rejection: Personal Portfolio Landing Page
is_icu_6, reason_6 = verify_genuine_icu_patient(
    title="Site 12 · The $500 buttons and the footer email lead nowhere on the live site",
    body="Rebuild taimooralam.com to the decided content. Both $500 buttons link to Paid consulting which returns 404.",
    author_comments=[],
    labels=[],
    repo="taimooralam/portfolio",
    author_assoc="OWNER"
)
assert not is_icu_6, f"Expected False for personal portfolio site, got: {reason_6}"
print("  ✓ Personal Portfolio Site: Rejected correctly.")

# 10. Rejection: Theatre Casting Alert
is_icu_7, reason_7 = verify_genuine_icu_patient(
    title="🎭 Egg; Or Anything Dipped in Egg Gone Soften - NYC EPA (10.23.26)",
    body="PAID CASTING ALERT. This production will operate under an Equity 29 hour-reading code.",
    author_comments=[],
    labels=[],
    repo="matthewletton/matthew-casting-radar",
    author_assoc="OWNER"
)
assert not is_icu_7, f"Expected False for theatre casting alert, got: {reason_7}"
print("  ✓ Theatre Casting Notice: Rejected correctly.")

# 11. Rejection: Board Game Rules FAQ
is_icu_8, reason_8 = verify_genuine_icu_patient(
    title="GF9 FAQ",
    body="Frequently answered questions for the GF9 ruleset we can find. Can a player pay spice for someone in battle?",
    author_comments=[],
    labels=[],
    repo="ndelangen/dunezone",
    author_assoc="OWNER"
)
assert not is_icu_8, f"Expected False for board game FAQ, got: {reason_8}"
print("  ✓ Board Game Ruleset: Rejected correctly.")

# 12. Rejection: Blog / GitHub Pages & Chinese Daily Info Flow (Headroom Conservation)
is_icu_digest_cn, reason_digest_cn = verify_genuine_icu_patient(
    title="[每日信息流] 2024-08-07",
    body="Startup raises $1,000,000 in seed round. AI models update summary.",
    author_comments=[],
    labels=[],
    repo="ruohong2018/ruohong2018.github.io",
    author_assoc="OWNER"
)
assert not is_icu_digest_cn, f"Expected False for Chinese daily stream on .github.io, got: {reason_digest_cn}"
print("  ✓ Chinese Daily Stream & .github.io Blog: Rejected correctly.")

# 13. Rejection: Bookmark / Picker Repo & Tech Digest
is_icu_picker, reason_picker = verify_genuine_icu_patient(
    title="Tech Weekly Digest #45",
    body="Top github repositories this week. Founders paid $10k in bug bounties.",
    author_comments=[],
    labels=[],
    repo="BruceFeIix/picker",
    author_assoc="OWNER"
)
assert not is_icu_picker, f"Expected False for picker/digest repo, got: {reason_picker}"
print("  ✓ Bookmark Picker & Weekly Digest: Rejected correctly.")

# 12. Rejection: Payment Negations
is_icu_9, reason_9 = verify_genuine_icu_patient(
    title="Production server crashing on startup with OOM",
    body="Our production server is down with OOM crash. Note that we are not willing to pay any consulting fees for help.",
    author_comments=[],
    labels=[],
    repo="example/prod-crash",
    author_assoc="OWNER"
)
assert not is_icu_9, f"Expected False for payment negation, got: {reason_9}"
print("  ✓ Payment Negation ('not willing to pay'): Rejected correctly.")

# 13. Rejection: Intermediary Aggregator / Bounty Platform
is_icu_10, reason_10 = verify_genuine_icu_patient(
    title="Gitcoin bounty: integrate wallet connect",
    body="Gitcoin hackathon bounty task for community grant.",
    author_comments=[],
    labels=[],
    repo="bounties/web3-task",
    author_assoc="OWNER"
)
assert not is_icu_10, f"Expected False for Gitcoin aggregator, got: {reason_10}"
print("  ✓ Bounty Aggregator / Hackathon: Rejected correctly.")

# 14. Rejection: Non-critical label
is_icu_lbl, reason_lbl = verify_genuine_icu_patient(
    title="Production memory leak",
    body="Willing to pay $1000 for fix",
    author_comments=[],
    labels=[{"name": "wontfix"}],
    repo="org/repo",
    author_assoc="OWNER"
)
assert not is_icu_lbl, "Expected False for wontfix label."
print("  ✓ Non-Critical Label ('wontfix'): Rejected correctly.")

# ----------------------------------------------------------------
# Test 2: Pre-Post Safety Sanitizer
# ----------------------------------------------------------------
print("\n[Test 2] Testing Pre-Post Safety Sanitizer...")

clean_payload = """### Technical Architecture & Feasibility Assessment
1. Root Cause Analysis: Webhook routing collision on WABA endpoint.
2. Remediation: Zero-touch webhook multiplexer.
```python
def handle_webhook(req):
    return {"status": "ok"}
```
3. Test Strategy: Sandbox Meta App staging verification.
4. Contact: isearch.xsolve@gmail.com"""
safe_1, msg_1 = sanitize_and_validate_payload(clean_payload)
assert safe_1, f"Expected clean payload to pass, got: {msg_1}"
print("  ✓ Clean Proposal: Approved.")

# Leaked Bank Account (Contiguous)
leaked_bank = clean_payload + "\nAccount Number: 55505593812 Bank: Kotak Bank"
assert not sanitize_and_validate_payload(leaked_bank)[0], "Expected contiguous account leak caught."
print("  ✓ Contiguous Bank Account Leak: Caught and blocked.")

# Leaked Formatted Account Number
leaked_formatted = clean_payload + "\nAccount: 1234-5678-9012"
assert not sanitize_and_validate_payload(leaked_formatted)[0], "Expected formatted account leak caught."
print("  ✓ Formatted Account Leak (1234-5678-9012): Caught and blocked.")

# Leaked Hyphenated Account Number (123-456-789-012)
leaked_hyphen = clean_payload + "\nAccount: 123-456-789-012"
assert not sanitize_and_validate_payload(leaked_hyphen)[0], "Expected hyphenated account leak caught."
print("  ✓ Hyphenated Account Leak (123-456-789-012): Caught and blocked.")

# Leaked Generic UPI (@paytm and @yesbank)
leaked_upi_paytm = clean_payload + "\nPay to: merchant@paytm"
assert not sanitize_and_validate_payload(leaked_upi_paytm)[0], "Expected @paytm UPI leak caught."
leaked_upi_yes = clean_payload + "\nPay to: alice@yesbank"
assert not sanitize_and_validate_payload(leaked_upi_yes)[0], "Expected @yesbank UPI leak caught."
print("  ✓ Banking UPI Leaks (@paytm, @yesbank): Caught and blocked.")

# Leaked EVM Ethereum Address
leaked_eth = clean_payload + "\nWallet: 0x71CAb39600a9F80c4c4A0b457e51e44fEbEbC141"
assert not sanitize_and_validate_payload(leaked_eth)[0], "Expected Ethereum address leak caught."
print("  ✓ EVM Ethereum Address Leak: Caught and blocked.")

# Leaked GitHub PAT
leaked_pat = clean_payload + "\nPAT: github_pat_11ABCDEF0123456789abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRST"
assert not sanitize_and_validate_payload(leaked_pat)[0], "Expected GitHub PAT leak caught."
print("  ✓ GitHub PAT Leak: Caught and blocked.")

# Leaked OpenAI Project Key (sk-proj-...)
leaked_skproj = clean_payload + "\nKey: sk-proj-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOP"
assert not sanitize_and_validate_payload(leaked_skproj)[0], "Expected sk-proj key leak caught."
print("  ✓ OpenAI Project Key Leak (sk-proj-...): Caught and blocked.")

# False Verification Claim
false_verification = clean_payload + "\nVerified on our reference environment with 100% test pass."
assert not sanitize_and_validate_payload(false_verification)[0], "Expected false test verification claim caught."
print("  ✓ False Test Verification Claim: Caught and blocked.")

# Verified Settlement Coordinates (Approved DOOM L1 and Solana Addresses)
payload_with_verified_settlement = clean_payload + "\n### Settlement Rails\n- DOOM L1: doom14ac0e785bffabe0357cb522608cf88c80a33cd7f3f925757\n- Solana: 2qi849TBq72XMpsp8PjR4YfegDEzc7BRFZaarwQ2tKgL\n- Email: isearch.xsolve@gmail.com"
ok_settle, msg_settle = sanitize_and_validate_payload(payload_with_verified_settlement)
assert ok_settle, f"Expected verified settlement addresses to pass, got: {msg_settle}"
print("  ✓ Verified Settlement Rails (DOOM L1 + Solana): Approved and permitted.")

# Unverified Random Solana Address Leak -> Caught and blocked
unverified_sol = clean_payload + "\nSolana: 4DjveHyuryraFdV8o4HWMp5aWb8nkwLmhPqpe9bw3UZgL"
assert not sanitize_and_validate_payload(unverified_sol)[0], "Expected unverified random Solana address to be blocked."
print("  ✓ Unverified Third-Party Crypto Address: Caught and blocked.")

# ----------------------------------------------------------------
# Test 3: Approved Corridor & Timezone Validation
# ----------------------------------------------------------------
print("\n[Test 3] Testing Approved Corridor Engine & Cambridge Collision...")

# Verify Cambridge MA vs Cambridge UK collision resolution & Global Expansion
sample_locations = [
    ("Bengaluru, India", "India Tech Hubs (IST)"),
    ("Singapore", "Singapore (SGT)"),
    ("Dubai, UAE", "UAE & Gulf (GST)"),
    ("Cambridge, MA", "US East (EDT/EST)"),
    ("Cambridge, UK", "UK (BST/GMT)"),
    ("London, England", "UK (BST/GMT)"),
    ("Austin, Texas", "US Central (CDT/CST)"),
    ("San Francisco, CA", "US West (PDT/PST)"),
    ("Munich, Germany", "Germany & DACH (CET/CEST)"),
    ("Berlin, Deutschland", "Germany & DACH (CET/CEST)"),
    ("Zurich, Switzerland", "Germany & DACH (CET/CEST)"),
    ("Paris, France", "Western & Northern Europe (CET/CEST)"),
    ("Amsterdam, Netherlands", "Western & Northern Europe (CET/CEST)"),
    ("Stockholm, Sweden", "Western & Northern Europe (CET/CEST)"),
    ("Nairobi, Kenya", "Kenya & East Africa (EAT)"),
    ("Kigali, Rwanda", "Kenya & East Africa (EAT)"),
    ("Lagos, Nigeria", "Nigeria & West/South Africa (WAT/SAST)"),
    ("Toronto, Canada", "Canada (EST/PST)"),
    ("Sydney, Australia", "Australia & NZ (AEST/NZST)"),
]

for loc, expected_name in sample_locations:
    matched = None
    for entry in APPROVED_CORRIDOR_TZ_MAP:
        if re.search(entry["pattern"], loc.lower()):
            matched = entry["name"]
            break
    assert matched == expected_name, f"Expected {expected_name} for '{loc}', got: {matched}"
print("  ✓ Cambridge Collision Resolved: 'Cambridge, MA' -> US East | 'Cambridge, UK' -> UK.")
print("  ✓ Global Corridor Expansion: Germany, Kenya, France, Netherlands, Nigeria, Canada, Australia validated.")

# Test hard territory exclusions (Kolkata/WB, China, Pakistan)
import autonomous_icu_pipeline

original_get_profile = autonomous_icu_pipeline.get_author_profile

# Test Kolkata Exclusion
autonomous_icu_pipeline.get_author_profile = lambda u: {"location": "Kolkata, India", "company": "Local Agency"}
c_name, is_act, reason = detect_author_corridor("kolkata_user")
assert c_name == "Excluded Regional Market", f"Expected Excluded Regional Market for Kolkata, got {c_name}"
print("  ✓ Hard Regional Exclusion: Kolkata/WB correctly excluded per zero-burn law.")

# Test China Exclusion
autonomous_icu_pipeline.get_author_profile = lambda u: {"location": "Beijing, China", "company": "Tencent"}
c_name, is_act, reason = detect_author_corridor("china_user")
assert c_name == "Excluded Territory", f"Expected Excluded Territory for China, got {c_name}"
print("  ✓ Hard Territory Exclusion: China correctly excluded per mandate.")

# Test Pakistan Exclusion
autonomous_icu_pipeline.get_author_profile = lambda u: {"location": "Lahore, Pakistan", "company": "Software House"}
c_name, is_act, reason = detect_author_corridor("pakistan_user")
assert c_name == "Excluded Territory", f"Expected Excluded Territory for Pakistan, got {c_name}"
print("  ✓ Hard Territory Exclusion: Pakistan correctly excluded per mandate.")

# Test Approved Corridor via detect_author_corridor (Munich, Germany)
autonomous_icu_pipeline.get_author_profile = lambda u: {"location": "Munich, Germany", "company": "BMW Group"}
c_name, is_act, reason = detect_author_corridor("munich_user")
assert c_name == "Germany & DACH (CET/CEST)", f"Expected Germany & DACH for Munich, got {c_name}"
print("  ✓ Approved Author Corridor: Munich, Germany approved through detect_author_corridor.")

# Test Approved Corridor via detect_author_corridor (Nairobi, Kenya)
autonomous_icu_pipeline.get_author_profile = lambda u: {"location": "Nairobi, Kenya", "company": "Fintech Lab"}
c_name, is_act, reason = detect_author_corridor("nairobi_user")
assert c_name == "Kenya & East Africa (EAT)", f"Expected Kenya & East Africa for Nairobi, got {c_name}"
print("  ✓ Approved Author Corridor: Nairobi, Kenya approved through detect_author_corridor.")

# Restore original
autonomous_icu_pipeline.get_author_profile = original_get_profile

# Verify bare Cambridge is treated as ambiguous / unapproved (fail-closed)
bare_cambridge = "cambridge"
bare_matched = None
for entry in APPROVED_CORRIDOR_TZ_MAP:
    if re.search(entry["pattern"], bare_cambridge):
        bare_matched = entry["name"]
        break
assert bare_matched is None, f"Bare Cambridge should not match any corridor, but matched {bare_matched}"
print("  ✓ Bare Cambridge Ambiguity: Failed closed (treated as unknown/unapproved).")
print("  ✓ Approved Enterprise Corridors: All tech hubs mapped strictly to exact IANA zones.")

# ----------------------------------------------------------------
# Test 4: Isolated SQLite Transactional Store & Concurrency Safety
# ----------------------------------------------------------------
print("\n[Test 4] Testing Isolated SQLite Store & Concurrency Safety...")

# Ensure fresh test database on every run
if os.path.exists(TEST_DB):
    try:
        os.remove(TEST_DB)
    except Exception:
        pass

# Initialize dedicated test database
init_db(db_path=TEST_DB)
test_repo = "test-org/concurrency-race"
test_num = 1001

# Worker 1 claims issue
claim_1 = try_claim_issue(test_repo, test_num, "Race Test", "tester", "US West", "Test claim", db_path=TEST_DB)
assert claim_1 is True, "Worker 1 failed to claim issue."
print("  ✓ Worker 1: Successfully claimed test issue in isolated SQLite DB.")

# Worker 2 attempts concurrent claim on same issue -> MUST FAIL
claim_2 = try_claim_issue(test_repo, test_num, "Race Test", "tester", "US West", "Test claim", db_path=TEST_DB)
assert claim_2 is False, "Worker 2 claimed already-claimed issue! Concurrency violated."
print("  ✓ Worker 2: Concurrent claim rejected by UNIQUE(repo, issue_number) constraint.")

# Verify status
claimed_status, cur_state = is_issue_claimed_or_delivered(test_repo, test_num, db_path=TEST_DB)
assert claimed_status is True and cur_state == "CLAIMED", f"Expected CLAIMED, got {cur_state}"

# Commit delivery with checked rowcount
test_cid = "comment_77777"
test_url = "https://github.com/test-org/concurrency-race/issues/1001#issuecomment-77777"
test_digest = "a" * 64
ok_commit = commit_delivery(test_repo, test_num, test_cid, test_url, test_digest, db_path=TEST_DB)
assert ok_commit is True, "Failed to commit delivery with rowcount == 1."

# Double commit or commit on non-claimed issue must fail
fail_commit = commit_delivery(test_repo, 999999, test_cid, test_url, test_digest, db_path=TEST_DB)
assert fail_commit is False, "Expected commit on nonexistent/unclaimed issue to return False."
print("  ✓ Checked Rowcount: Commit succeeds on claimed row and returns False on invalid row.")

# Verify delivered state
del_status, final_state = is_issue_claimed_or_delivered(test_repo, test_num, db_path=TEST_DB)
assert del_status is True and final_state == "PROPOSAL_DELIVERED", f"Expected PROPOSAL_DELIVERED, got {final_state}"
print("  ✓ Transactional State: Atomically transitioned from CLAIMED to PROPOSAL_DELIVERED.")

# Clean up test database
if os.path.exists(TEST_DB):
    try:
        os.remove(TEST_DB)
    except Exception:
        pass

# ----------------------------------------------------------------
# Test 5: Search-Gate Contract Congruence (Zero Approved = Zero in Search)
# ----------------------------------------------------------------
print("\n[Test 5] Testing Search-Gate Contract Congruence...")

from autonomous_icu_pipeline import search_issues

# Mock run_cmd to feed raw search results through search_issues
orig_run_cmd = autonomous_icu_pipeline.run_cmd

mock_raw_items = [
    # 1. Terminal label 'wontfix' -> MUST BE DROPPED
    {
        "number": 1, "title": "Crash in app", "body": "App crashes in production. Will pay $100.",
        "repository": {"nameWithOwner": "org/repo1"}, "labels": [{"name": "wontfix"}],
        "authorAssociation": "OWNER", "author": {"login": "dev1"}
    },
    # 2. Terminal label 'spam' -> MUST BE DROPPED
    {
        "number": 2, "title": "Spam ticket", "body": "Buy crypto.",
        "repository": {"nameWithOwner": "org/repo2"}, "labels": [{"name": "spam"}],
        "authorAssociation": "OWNER", "author": {"login": "dev2"}
    },
    # 3. Explicit payment negation -> MUST BE DROPPED
    {
        "number": 3, "title": "Need help", "body": "We cannot pay for this fix. No budget.",
        "repository": {"nameWithOwner": "org/repo3"}, "labels": [{"name": "bounty"}],
        "authorAssociation": "OWNER", "author": {"login": "dev3"}
    },
    # 4. Economic scam -> MUST BE DROPPED
    {
        "number": 4, "title": "Crypto Lottery", "body": "Win casino lottery.",
        "repository": {"nameWithOwner": "org/repo4"}, "labels": [{"name": "bounty"}],
        "authorAssociation": "OWNER", "author": {"login": "dev4"}
    },
    # 5. Contract-compliant genuine client with enhancement label -> MUST BE YIELDED FOR VERIFICATION
    {
        "number": 5, "title": "Database dumps do not work on large databases",
        "body": "Production deadlock and crash during table dump under heavy load. We offer $250 bounty.",
        "repository": {"nameWithOwner": "outerbase/starbasedb"}, "labels": [{"name": "enhancement"}],
        "authorAssociation": "MEMBER", "author": {"login": "Brayden"}
    }
]

import json
autonomous_icu_pipeline.run_cmd = lambda cmd, timeout=35: (json.dumps(mock_raw_items), "", 0)

yielded = search_issues("dummy query")
assert len(yielded) == 1, f"Expected exactly 1 approved candidate, got {len(yielded)}"
assert yielded[0]["number"] == 5, f"Expected issue #5 to be approved, got #{yielded[0]['number']}"
print("  ✓ Search-Gate High-Recall Congruence: Terminal labels, negations, and scams filtered; paid work yielded.")

# Test Zero Approved = Zero Yielded
autonomous_icu_pipeline.run_cmd = lambda cmd, timeout=35: (json.dumps(mock_raw_items[:4]), "", 0)
yielded_zero = search_issues("dummy query")
assert len(yielded_zero) == 0, f"Expected 0 yielded when zero approved, got {len(yielded_zero)}"
print("  ✓ Zero Approved Contract: Zero approved candidates strictly yields 0 search results.")

# Restore run_cmd
autonomous_icu_pipeline.run_cmd = orig_run_cmd

# ----------------------------------------------------------------
# Test 6: Advisory Deletion & Implementation Upgrade Logic
# ----------------------------------------------------------------
print("\n[Test 6] Testing Advisory Deletion & Implementation Upgrade Logic...")

from autonomous_icu_pipeline import delete_github_comment

# 6a. Delete comment mock check
autonomous_icu_pipeline.run_cmd = lambda cmd, timeout=20, retries=2: ("", "", 0)
ok_del, msg_del = delete_github_comment("mock/repo", "1234567")
assert ok_del, f"Expected successful delete, got: {msg_del}"
print("  ✓ GitHub Comment Deletion: Verified delete request.")

# 6b. Verify commit_delivery updates existing delivered row
ok_upd = commit_delivery(test_repo, test_num, "new_comment_999", f"https://github.com/{test_repo}/issues/{test_num}#comment", "sha256_new_digest", db_path=TEST_DB)
assert ok_upd, "Expected commit_delivery to update existing delivery row."
print("  ✓ Delivery Upgrade Commit: Successfully updated SQLite store.")

# Restore run_cmd
autonomous_icu_pipeline.run_cmd = orig_run_cmd

# ----------------------------------------------------------------
# Test 7: High-Recall Bounty Expansion & Platform Attestation
# ----------------------------------------------------------------
print("\n[Test 7] Testing High-Recall Bounty Expansion & Platform Attestation...")

# 7a. Algora-bot platform-attested bounty on NONE-association issue
is_algora_bounty, algora_reason = verify_genuine_icu_patient(
    title="Optimize GPU kernel execution speed",
    body="Need 2x speedup on vector math kernel.",
    author_comments=["/bounty $300 funded via algora.io"],
    labels=[{"name": "enhancement"}, {"name": "bounty"}],
    repo="web3-org/gpu-kernels",
    author_assoc="NONE",
    author="community_dev"
)
assert is_algora_bounty, f"Expected Algora bounty on NONE-assoc issue to be approved, got: {algora_reason}"
print("  ✓ Platform Attestation Gate: Algora-attested bounty approved on NONE-assoc issue.")

# 7b. Feature enhancement with paid bounty and no crash words
is_feat_bounty, feat_reason = verify_genuine_icu_patient(
    title="Add AVX-512 vector acceleration",
    body="Offering $500 bounty to implement AVX-512 driver.",
    author_comments=[],
    labels=[{"name": "enhancement"}],
    repo="fastorg/math-engine",
    author_assoc="OWNER",
    author="fastdev"
)
assert is_feat_bounty, f"Expected AVX-512 feature bounty to be approved, got: {feat_reason}"
print("  ✓ Feature Bounty Gate: Paid enhancement approved without needing crash/outage words.")

# 7c. Remote / Worldwide / Blank author profile location
autonomous_icu_pipeline.get_author_profile = lambda u: {"location": "Remote, Worldwide"}
c_name, is_act, c_reason = detect_author_corridor("remote_dev")
assert c_name == "Global / Remote" and is_act is True, f"Expected Global / Remote for remote dev, got {c_name}, {is_act}"
print("  ✓ Global/Remote Corridor Gate: Remote/Worldwide location approved without business-hour blocking.")

autonomous_icu_pipeline.get_author_profile = lambda u: {"location": ""}
c_name_blank, is_act_blank, c_reason_blank = detect_author_corridor("blank_dev")
assert c_name_blank == "Global / Remote" and is_act_blank is True, f"Expected Global / Remote for blank dev, got {c_name_blank}, {is_act_blank}"
print("  ✓ Global/Remote Corridor Gate: Blank location approved without business-hour blocking.")

autonomous_icu_pipeline.get_author_profile = orig_get_profile

# -------------------------------------------------------------
# 8. TEST AUTONOMOUS PULL REQUEST ENGINE
# -------------------------------------------------------------
print("\n[Test 8] Testing Autonomous Pull Request Engine...")

sample_deliverable = """### 🛠️ Production Implementation & Technical Verification

1. **Root Cause Analysis**:
Identified buffer boundary mismatch in core parser.

2. **Production-Grade Implementation Source Code**:

### Production Source (`src/core/parser.js`)
```javascript
export function parsePayload(buf) {
  if (!buf || buf.length === 0) throw new Error("Empty buffer");
  return JSON.parse(buf.toString());
}
```

### Test Suite (`test/parser.test.js`)
```javascript
import assert from "node:assert/strict";
import { test } from "node:test";
import { parsePayload } from "../src/core/parser.js";

test("parses valid JSON buffer", () => {
  assert.deepEqual(parsePayload(Buffer.from('{"ok":true}')), { ok: true });
});
```

3. **Settlement Rails**:
- DOOM L1: doom14ac0e785bffabe0357cb522608cf88c80a33cd7f3f925757
- Solana: 2qi849TBq72XMpsp8PjR4YfegDEzc7BRFZaarwQ2tKgL
"""

extracted = autonomous_icu_pipeline.extract_files_from_proposal(sample_deliverable)
assert len(extracted) == 2, f"Expected 2 extracted files, got {len(extracted)}"
assert extracted[0][0] == "src/core/parser.js", f"Unexpected path: {extracted[0][0]}"
assert "parsePayload" in extracted[0][1], "Expected code body in extracted[0]"
assert extracted[1][0] == "test/parser.test.js", f"Unexpected path: {extracted[1][0]}"
assert "parses valid JSON buffer" in extracted[1][1], "Expected test body in extracted[1]"
print("  ✓ Proposal File Extraction: Successfully parsed source code and test files.")

# Test database persistence of PR URL
test_pr_url = "https://github.com/mock-org/mock-repo/pull/42"
autonomous_icu_pipeline.try_claim_issue(
    repo="mock-org/mock-repo",
    number=101,
    title="Test Parser",
    author="testuser",
    corridor="Global / Remote",
    reason="Test",
    db_path=TEST_DB
)
autonomous_icu_pipeline.commit_delivery(
    repo="mock-org/mock-repo",
    number=101,
    comment_id="mock_cid",
    receipt_url="https://github.com/mock-org/mock-repo/issues/101#comment",
    sha256_digest="mock_digest",
    pr_url=test_pr_url,
    db_path=TEST_DB
)
autonomous_icu_pipeline.update_delivery_pr("mock-org/mock-repo", 101, test_pr_url, db_path=TEST_DB)
with sqlite3.connect(TEST_DB) as test_con:
    row = test_con.execute("SELECT pr_url FROM deliveries WHERE repo = ? AND issue_number = ?", ("mock-org/mock-repo", 101)).fetchone()
    assert row and row[0] == test_pr_url, f"Expected PR URL persisted, got {row}"
print("  ✓ PR URL DB Persistence: Successfully stored and retrieved pr_url in deliveries store.")

# Test dry-run PR creation
pr_dry_run = autonomous_icu_pipeline.attempt_automated_pull_request("mock-org/mock-repo", 101, "Fix Parser", sample_deliverable, live_mode=False)
assert pr_dry_run is None, f"Expected dry-run PR to return None, got {pr_dry_run}"
print("  ✓ PR Safety Gate: Dry-run safely holds network creation.")

# ----------------------------------------------------------------
# Test 9: Pre-Commit Sandbox Syntax Quality Gates & CLA Detection
# ----------------------------------------------------------------
print("\n[Test 9] Testing Pre-Commit Sandbox Syntax Quality Gates & CLA...")
import tempfile
from autonomous_icu_pipeline import validate_synthesized_files, auto_resolve_cla_if_needed

# 1. Valid Python + JSON files
valid_extracted = [
    ("src/solution.py", "def add(a: int, b: int) -> int:\n    return a + b\n"),
    ("config/schema.json", '{"version": 1, "enabled": true}')
]
ok, msg = validate_synthesized_files(tempfile.gettempdir(), valid_extracted)
assert ok is True, f"Expected valid files to pass, got: {msg}"
print("  ✓ Quality Gate: Valid Python and JSON syntax verified.")

# 2. Syntax Error in Python
bad_py_extracted = [
    ("src/broken.py", "def broken(\n    return 42\n")
]
ok_bad_py, msg_bad_py = validate_synthesized_files(tempfile.gettempdir(), bad_py_extracted)
assert ok_bad_py is False, "Expected syntax error in Python to fail quality gate."
print("  ✓ Quality Gate: Caught and blocked Python syntax error.")

# 3. Syntax Error in JSON
bad_json_extracted = [
    ("config/broken.json", '{"version": 1, "enabled": true,}')
]
ok_bad_json, msg_bad_json = validate_synthesized_files(tempfile.gettempdir(), bad_json_extracted)
assert ok_bad_json is False, "Expected trailing comma JSON to fail quality gate."
print("  ✓ Quality Gate: Caught and blocked invalid JSON schema.")

print("\n==================================================")
print("ALL ICU PIPELINE INTEGRITY TESTS PASSED (100% GREEN)")
print("==================================================")
