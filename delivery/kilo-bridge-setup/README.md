# Kilo Bridge employment setup

This package launches the employment mission agent through the installed OpenCode CLI and the existing Agent360 browser MCP. `-Launch` is the agent mission entry point; it does not run the deterministic lane scripts as a substitute for the agent.

## Client prerequisites

- Windows PowerShell 5.1 or PowerShell 7
- Python 3.11+ and Node.js 20+
- Google Chrome with the Agent360 extension installed and connected
- The required job-site sessions already signed in, in the Chrome profile attached to Agent360
- `@agent360/browser-mcp`; install into this package with `-InstallMcp` if it is not already present
- OpenCode CLI configured with the Agent360 browser MCP

The runner never enters passwords or OTPs. Sign in manually before running. Browser actions use the Agent360 MCP interface only.

## Run

From this folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\kilo-bridge-setup.ps1 -InstallMcp
Copy-Item .\candidate-profile.example.json .\candidate-profile.json
Copy-Item .\scripts\apply_answers.example.txt .\candidate-answers.txt
# Edit candidate-profile.json and candidate-answers.txt with verified, candidate-specific data.
powershell -ExecutionPolicy Bypass -File .\kilo-bridge-setup.ps1 -Launch
```

The setup/install step is allowed before candidate data is configured. `-Launch` requires a
valid candidate profile, a hash-verified resume, at least two verified skills, and the
configured private answers file.

`-Launch` validates the local runtime, MCP package, candidate config, resume hash and answer file, then starts the OpenCode agent with the mission documents and existing ledger attached. It does not perform the five-lane deterministic runner in place of the agent. Agent output is saved to `evidence\employment-lane\mission-agent-output.txt`; the launcher log is saved to `evidence\employment-lane\mission-agent-run.log`. Review screenshot and ledger receipts before treating any mission item as complete.

### Limit one application to a specific role

The mission agent can be limited to one exact role by providing the title currently shown as `MATCHED`:

```powershell
powershell -ExecutionPolicy Bypass -File .\kilo-bridge-setup.ps1 -Launch -SubmitOne -Title "Exact matched role title"
```

The mission remains subject to the fit, candidate-fact, one-submit, and receipt gates in `MISSION-RUN.txt` and `docs\EMPLOYMENT-LANE-MISSION.md`. The title limits application submission for that run; it does not switch `-Launch` back to the deterministic lane scripts.

## Receipts and profile data

- Copy `candidate-profile.example.json` to a private `candidate-profile.json`; set the candidate's resume path, SHA256, verified skills, and private answer-file path. Copy `scripts\apply_answers.example.txt` to that private answer file and add only candidate-confirmed facts. Never ship a candidate's resume or answer file in a client package.
- Mission tool directives: `MISSION-RUN.txt` and `docs\EMPLOYMENT-LANE-MISSION.md`. These direct an agent to use Agent360's existing browser tools for visible UI actions; they do not claim that every lane has already passed.
- Browser and lane code: `scripts\`
- E2E screenshots and ledger: `evidence\employment-lane\`
- No credentials are written to this package by the setup script.

The working copy includes candidate-specific evidence of one Naukri application confirmed in history. That receipt is not a client result. Profile updates, Foundit/Indeed/LinkedIn submissions, and LinkedIn comment publication still lack live receipts. Re-run against the target operator's account after the current static fixes before describing the setup as ready to ship. Do not distribute this working folder as-is: it contains local candidate data and evidence; prepare a sanitized client copy first.
