# GHOST-CLEANUP REPORT — 2026-09-13T19:02→19:20Z (Baba order, workdir D:\anonym)

LAW COMPLIANCE: no radio-touching command was ever issued (no airplane/cmd connectivity/telephony service calls — only `settings get` reads). No processes killed (no Force stop taps). Desktop Chrome untouched — no windows opened in any profile; all UI work on PHONE Chrome via adb + CLI. No WhatsApp tab opened. No contact with Raktima. Author name for anything public stays NILOY DAS (nothing published here).

---

## TASK 1 — kunal.colab residual Google toggles: VERIFIED COMPLETE (no action needed)

Path: `adb shell input keyevent KEYCODE_WAKEUP` → `adb shell wm dismiss-keyguard` → `adb shell "am start -a android.intent.action.VIEW -d 'https://myactivity.google.com/activitycontrols'"` → `uiautomator dump` ×2 (before/after).

Account chip (in-page element, the only valid session proof per burn-ledger truth-note):
> `Google Account: Kunal Das (kunal.colab@gmail.com), Google membership` — correct account, no chip switch needed.

Final state read from live DOM text (activitycontrols-before.xml = after.xml, nothing changed):

| Toggle | State | Proof text in dump |
|---|---|---|
| Personalised Recommendations in Search services | **OFF** | `Off since 14 September 2026` → button `Start getting personalised recommendations...` |
| Web & App Activity | **OFF** | `Off since 13 September 2026` → button `Turn on Web & App Activity` |
| YouTube History | **OFF** | button offers `Turn on YouTube History` (+ `A subsetting was last updated on 14 September 2026`) |
| Play personalisation | **ON — OBSERVATION** | `On` / `Stop personalising your Play experience` — outside task scope, not touched; Baba to decide (ledger row for kunal.colab claimed Play already off — page disagrees). |

No password gate appeared → no 'needs Baba' on this task. The "residue: search-recs + YT" from the GOOGLE BURN LEDGER is now CLOSED — search-recs shows off since 14 Sep 2026 (IST), i.e. completed between the 18:56Z session digest and this audit; GHOST verified but did not need to click.

## TASK 2 — Truecaller: NOT PRESENT

- `adb shell "pm list packages | grep -i truecaller"` → empty. Nothing to uninstall (no `pm uninstall` executed).
- Residual exposure lives server-side → Baba must unregister the number at https://www.truecaller.com/unregister (needs phone OTP → that is a guardian window / weekly-blink event, not this agent).

## TASK 3 — vivo (iQOO/BBK) account: RECORDED, NOTHING DESTRUCTIVE

- `pm list packages | grep -i bbk` → 12 packages incl. `com.bbk.account`, `com.bbk.cloud`. No uninstall/disable attempted.
- Account IS signed in: `dumpsys account` shows exactly one authenticator entry `type=BBKOnLineService` with a masked email (`xxxxxxx.xxxxxx@xxxxx.xxx` — Android masks names in shell dumps; Baba can read it on-screen).
- Launch reality: `com.bbk.account` has NO launcher activity (`monkey -c LAUNCHER` → "No activities found"). Direct entry used: `am start -n com.bbk.account/.activity.LauncherActivity` → lands on **consent dialog**: "iQOO Account — Use the services offered in system apps more smoothly with iQOO Account. Enjoy after-sales services including an E-warranty card..." with buttons `Disagree` / `Agree`. **Neither was tapped** (tapping Agree = accepting BBK privacy terms on Baba's behalf; left pure). Phone sent HOME afterwards.
- Exact steps for Baba (to reach sign-out himself):
  1. Open **Settings** → top banner row **iQOO Account** (the account email under the phone-model header), or dialer-free path used here: app is `com.bbk.account` → App info (see 4).
  2. Consent dialog above → **Agree** (his decision) → account home shows profile/sign-in.
  3. Sign-out requires **the vivo account password** — screen: Profile → Sign out → password prompt. GHOST did NOT go past the consent dialog (no sign-out clicks).
  4. Alternative neutralization without his password: Settings→Apps→Special app access→Modify system settings list for `com.bbk.account` (dumped) shows buttons — App info has **"Disable"** (top-right) — disabling is reversible, non-destructive, kills app function without password. Not touched; Baba's call. (Force stop deliberately NOT pressed — process-kill law.)

## TASK 4 — Chrome geo policy: CONFIRMED

- `reg query "HKLM\SOFTWARE\Policies\Google\Chrome"` →
  `DefaultGeolocationSetting REG_DWORD 0x2` (=2, block) + `GeolocationDecisionPreauthorizationEnabled 0x0` + subkey `...\Chrome\GeolocationBlocked` with value `1 REG_SZ *://*/*` (all sites blocked).
- Write provenance found in `war-log/sudo-hands.log`: policy written **2026-09-13T15:08:42.159Z** (`CHROME POLICY: geolocation default=BLOCK, ALL SITES GEO-BLOCKED (survives restarts)`).
- Restart-pending truth: running Chrome process groups span launches 2:39 PM IST (pre-write) through 12:31 AM IST (post-write). Chrome polls machine policies (~30 min) so long-lived profiles should pick it up without restart, but per protocol the law is *guaranteed* at next launch; pre-15:08Z browser groups still exist. NOT verified via chrome://policy — prohibited (main Chrome belongs to LINE-AGENT).

## TASK 5 — Health: ALL GREEN

| Check | Result |
|---|---|
| GET 8768/status?token=GOLD24 | `radioOff:true, busy:false, waiting:0, stuck:false, blinkCount:1, lastWindow 12:21:49Z` |
| GET 8777/health | `relay-live, bank 28024, reports 7` |
| GET 8769/health | `sudo-hands ok, elevated:true` |
| GET 8768/callwindow | `windowUntil:0, active:false` — idle, no open window |
| adb read-only | `settings get global airplane_mode_on` → **1** |

Transparency note: blink-log tail shows `RADIO-REKILL` at 19:03:56Z and 19:04:09Z (during Task-3 vivo-app probing). GHOST issued zero telephony/connectivity commands — the OS itself woke the radio (sporadic events also logged all day: 15:28, 15:30, 16:03, 18:41Z); guardian re-killed within seconds and final status confirms POWER_OFF. No new window granted; exposure delta 0 s attributed to this agent.

## EVIDENCE FILES (war-log is gitignored — proof stays local; copy of this report in tools/ is committed)

- `D:\anonym\war-log\evidence\ghost\activitycontrols-before.xml` (DOM proving chip=kunal.colab + 3 toggles OFF)
- `D:\anonym\war-log\evidence\ghost\activitycontrols-after.xml` (identical re-dump, stability proof)
- `D:\anonym\war-log\evidence\ghost\bbk-account-ui.xml` (iQOO consent dialog text)
- `D:\anonym\war-log\evidence\ghost\bbk-appinfo.xml` (App info: Disable button, 32.21 MB, storage/permissions rows)
- Inline in this report: reg query output + sudo-hands.log policy-write line.

## WHAT BABA MUST DO NEXT

1. **Truecaller web unregister** — https://www.truecaller.com/unregister (number-side residue; will need a guardian SMS window — queue it weekly, not urgent).
2. **vivo account** — decide: sign out (needs his vivo password; steps in §3) or press **Disable** on the app-info screen (steps §3.4, reversible, no password). Do NOT use Force stop.
3. **Optional review**: kunal.colab **Play personalisation = ON** and ad personalisation = ON today (page truth vs ledger) — say the word and next login session can flip them; kunal.colab **password not needed tonight** (no gate hit).
4. Ensure any still-running older Chrome browser groups get a full quit-and-relaunch when LINE-AGENT is idle, so the geo block applies at guaranteed launch-time.

LEDGER: skipped per order (money lane only).
