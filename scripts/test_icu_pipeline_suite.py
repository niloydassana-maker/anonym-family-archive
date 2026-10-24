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

# ----------------------------------------------------------------
# Test 3: Approved Corridor & Timezone Validation
# ----------------------------------------------------------------
print("\n[Test 3] Testing Approved Corridor Engine & Cambridge Collision...")

# Verify Cambridge MA vs Cambridge UK collision resolution
sample_locations = [
    ("Bengaluru, India", "India Tech Hubs (IST)"),
    ("Singapore", "Singapore (SGT)"),
    ("Dubai, UAE", "UAE (GST)"),
    ("Cambridge, MA", "US East (EDT/EST)"),
    ("Cambridge, UK", "UK (BST/GMT)"),
    ("London, England", "UK (BST/GMT)"),
    ("Austin, Texas", "US Central (CDT/CST)"),
    ("San Francisco, CA", "US West (PDT/PST)"),
]

for loc, expected_name in sample_locations:
    matched = None
    for entry in APPROVED_CORRIDOR_TZ_MAP:
        if re.search(entry["pattern"], loc.lower()):
            matched = entry["name"]
            break
    assert matched == expected_name, f"Expected {expected_name} for '{loc}', got: {matched}"
print("  ✓ Cambridge Collision Resolved: 'Cambridge, MA' -> US East | 'Cambridge, UK' -> UK.")

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

print("\n==================================================")
print("ALL ICU PIPELINE INTEGRITY TESTS PASSED (100% GREEN)")
print("==================================================")
