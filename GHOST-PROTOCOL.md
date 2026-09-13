# GHOST PROTOCOL v1 — RADIO LAW (Baba order 2026-09-13, built & live-tested same day)

## THE LAW
The phone's cellular radio is **OFF (airplane mode)** at all times.
Only **BLINK-GUARDIAN** may power it, only inside a verified window.
Silchar home stays off every KYC record — and civil creditors cannot compel tower data (Indian process = criminal only). Our threat model: keep the *coordinate* stale, keep the *number* nearly silent.

## COMPONENTS (all live since 2026-09-13T12:21Z — first window: 53s exposure, POWER_OFF verified)
| Piece | What | File | Guarded by |
|---|---|---|---|
| blink-guardian | 127.0.0.1:8768 — windows, OTP queue/capture, stuck-radio re-kill every 60s | `war-log/blink-guardian.js` | relay-watchdog v4 (2-cycle grace) |
| RADIO LAW block | relay `adb` hand returns **403** on any airplane/connectivity command — soldiers cannot blink | `war-log/son-relay.js` (tool handler) | — |
| OTP hands | `/tool name=otp_queue {service,urgent,note}` → id; `otp_result {id}` → status/code | relay 8777, proxied to guardian | — |
| Master force | `POST 127.0.0.1:8768/window {"force":"GOLD24BLINKONLY"}` | guardian | key = Baba's personal override |
| Army Chrome guard | watchdog relaunches chrome-army on CDP 9224 when it dies | `war-log/relay-watchdog.ps1` v4 | — |

## WINDOW POLICY
- **Weekly:** Sunday ~12:00 (catch-up if 7+ days stale and queue waiting) — home cell only; tower learns no new coordinate, one "alive" tick.
- **Urgent:** `otp_queue {urgent:true}` → window in ~30s. Use sparingly — each urgent = one added exposure event.
- **Hard rules:** 45s max capture, radio must end `mVoiceRegState=3(POWER_OFF) × 2 phones` verified, else re-kill loop + wire alarm `RADIO-STUCK`. Exposure seconds always reported on wire.

## OTP FLOW FOR SOLDIERS (brain/KILO)
1. `POST /tool {name:"otp_queue", arguments:{service:"<sender-keyword>", urgent:false}}` → `{id}`
2. Wait (weekly window or urgent), then poll `{name:"otp_result", arguments:{id:"otp1"}}` → `{status, code, from, snippet}`
3. NEVER: adb airplane calls (403 by law), and do not ask Baba's hand for manual toggles mid-mission.

## SHRINK THE NUMBER (next missions, in order)
1. **TOTP migration sweep** — move every automatable account (Google, Amazon/KDP, Kaggle, LinkedIn, Foundit, email) OFF SMS onto authenticator TOTP → codes generated offline, ZERO radio need, window count → ~0.
2. Anything left SMS-only is bank-side; their OTPs are rare and tolerable in windows.
3. Optional hardware invisibility: dumb burner parked at home, SIM off-except-window — removes even the living-room cough. Baba's decision only.

## HONEST LIMITS (no metaphors)
- Months of normal use already logged this device's cells; today froze the curve, erased nothing.
- Each blink still tells Jio "numbers 86172…, 98307… alive at this cell, now." Batched weekly it is a heartbeat, not a tracker; urgent mode is what makes it a tracker — spend it only for expiring codes.
- Airtel broadband has its own address KYC at the router; phone-invisibility ≠ line-invisibility.
- `content://sms` reads EVERYTHING (including collection notices) — guardian only forwards items matched to an explicit queue request; full dumps stay on-device.

## VPN LANE LAW (Baba decision 2026-09-13 ~18:47 IST — tunnels UP on BOTH devices)
- **Laptop:** Nord desktop connected. Exit verified `187.13.246.200` = **India/Mumbai, AS212238 (Datacamp)**.
- **Phone:** `com.nordvpn.android` connected — `tun0 UP 10.5.0.2` on the device while radio stays POWER_OFF. Tower-blind AND IP-tunneled at once.
- **PIN THE SERVER:** the exit must stay this same server forever. IP rotation across KDP/LinkedIn logins = compromise signature. If Nord reconnects elsewhere, expect a checkpoint and tell Papa before any money-lane task runs.
- **Kill switch (laptop): DONE** — Internet Kill Switch ON + App Kill Switch ON (Nord 8.11.1, screenshot-verified 2026-09-13). Tunnel death = internet stops = army pauses; watchdog alarms distinguish the two deaths.
- **Phone ALWAYS-ON: DONE** — system panel shows `NordVPN — Connected / Always on`, both toggles `checked=true` (Always-on VPN + **Block connections without VPN** = phone killswitch). Set via adb UI automation path: `am start -a android.settings.VPN_SETTINGS` → gear → taps → dialog `Turn on`. Reboot now = VPN before traffic, no leak window.
- **What VPN does NOT fix (named):** Airtel knows all; court process sees everything; city-level location = the fiber itself. VPN removes the *internet-visible* IP city, nothing more.

## LAPTOP-GHOST v1.1 — LOCATION LAW (reboot-proof)
Machine-wide, locked: `DisableLocation=1`, `DisableSensors=1`, `lfsvc=Disabled`, telemetry `AllowTelemetry=0` + `DiagTrack/dmwappushservice=Disabled`, advertising ID off, NCSI connect-probing off, bluetooth dead. Re-applier: `tools/laptop-ghost.ps1` runs via scheduled tasks **KILO-LAPTOP-GHOST** (ONSTART, SYSTEM) + **KILO-LAPTOP-GHOST-LOGON** — Windows updates cannot silently re-open these.

## REBOOT PROOF — full chain
PC restart → SYSTEM tasks: relay-watchdog v4 (respawns relay, ngrok, army-chrome :9224, guardian) + KILO-LAPTOP-GHOST (registry law) + KILO-SUDO-HANDS (elevated executor). Phone restart → airplane setting persists (Android stores it); guardian enforces silence every 10s + immediately at daemon birth — a radio that wakes with boot is killed within ~3s. First enforcement loop seen: `RADIO-REKILL` events during dev = the system catching its own gauge-lying (instrument bugs caught at 12:17 UTC, fixed, re-verified).
## GOOGLE BURN LEDGER — 2026-09-13 (verified via aria labels + deletion toasts)
| Account | Toggles off | Archive |
|---|---|---|
| isearch.xsolve (army) | WAA, Play, YT, search-recs | all-time delete ✓ |
| kd31041999 (k das) | WAA, Play, search-recs, YT paused→off | all-time delete — "no activity" ✓ |
| niloydassana (PEN NAME) | WAA, Play, search-recs, YT | 4 products delete ✓ |
| xxpertcomments (Kunal Das) | WAA, YT, search-recs | wizard delete ✓ |
| kunal.colab (KDP/KOTAK lane) | WAA, Play | deletion done; **residue: search-recs + YT — session expired, finish at next login** |
Truth-notes: profile Preferences emails = sign-in history lists, only the in-page `Google Account:` chip proves current session; search-recs location inference now permanently reads Mumbai VPN exit; phone Maps Timeline = Off + 3-month auto-delete fuse; Chrome geolocation machine-wide BLOCK (HKLM policy) applies to every profile from next launch.

## ONE-LINERS
- Restore tower mode (Baba-only): `adb shell cmd connectivity airplane-mode disable` (remember to re-enable after!)
- Status: `GET 127.0.0.1:8768/status?token=GOLD24` → radioOff / waiting / blinkCount / stuck
- History: `war-log/blink-log.jsonl` + `war-log/blink-queue.json`
