# Anonym Setup — Status 2026-09-02

## DONE (all working, verified)

1. Windows Location disabled
2. VirtualBox 7.2.16 installed
3. VT-x enabled via ENABLE VIRTUALIZATION.cmd (Lenovo WMI, no BIOS visit needed)
4. Whonix-Gateway + Whonix-Workstation imported, both RUNNING (GUI windows open)

## Do now (inside the VM windows)

1. Whonix-Gateway window → wait for "Tor: connected" (green, up to a few min)
2. Whonix-Workstation window → first boot: set a NEW password for user `user`
3. Do all private work ONLY inside Whonix-Workstation.
4. NEVER log into your original Gmail inside Whonix.

## Files in this folder

| File | Purpose |
|------|---------|
| Whonix-Gateway.ova | Whonix 18.2.1.9 (Gateway + Workstation) |
| tails-amd64-7.11.iso | Tails 7.11 live USB image |
| start-whonix.bat | Launcher: Gateway → Tor → Workstation |
| VirtualBox-7.2.16-Setup.exe | VBox installer (can delete after setup) |
| disable-location.ps1 | Location-disabling script (already ran) |

## Optional: Tails USB (max no-trace sessions)

Plug in any USB stick (8 GB+) and tell Kilo: "write Tails to USB".
It will burn tails-amd64-7.11.iso to the stick.

## Cleanup (optional)

VirtualBox-Setup.exe (old 7.1.4) and VirtualBox-7.2.16-Setup.exe can be deleted.

## Need help?

Tell Kilo: "continue the anonym setup" — it has full memory of everything done.
