# Collaborator Invite Checklist — READ-ONLY
Target GitHub user: **prafullprince** (email: prafullprince12@gmail.com)
Permission to select in the dropdown: **Read** (NOT Write — the dropdown defaults to Write!)

For each repo below:
1. Open the link (goes straight to Settings → Collaborators)
2. Click **Add people**
3. Paste: `prafullprince12@gmail.com` (or type username: `prafullprince`)
4. **Change the permission dropdown from "Write" to "Read"**
5. Click **Add to repository**

Done: [ ] | Done: [ ] | Done: [ ] — mark as you go.

---

## The 49 Repositories

1. [ ] https://github.com/isearchxsolve/_fleet_flutter_release_20260817/settings/access
2. [ ] https://github.com/isearchxsolve/_fleet_flutter_release_attempt2_20260817/settings/access
3. [ ] https://github.com/isearchxsolve/_live_flutter_verification_20260817/settings/access
4. [ ] https://github.com/isearchxsolve/_live_proof_fastapi_react_20260822/settings/access
5. [ ] https://github.com/isearchxsolve/ack/settings/access
6. [ ] https://github.com/isearchxsolve/ai_video_monetizer/settings/access
7. [ ] https://github.com/isearchxsolve/antigravity-kandover/settings/access
8. [ ] https://github.com/isearchxsolve/api_money_bot_complete/settings/access
9. [ ] https://github.com/isearchxsolve/ases_v3_1/settings/access
10. [ ] https://github.com/isearchxsolve/claude_code_clone/settings/access
11. [ ] https://github.com/isearchxsolve/convergence_framework/settings/access
12. [ ] https://github.com/isearchxsolve/crypto-ai-auto-trader/settings/access
13. [ ] https://github.com/isearchxsolve/crypto-app-by-replit/settings/access
14. [ ] https://github.com/isearchxsolve/crypto-trading-ai-agent/settings/access
15. [ ] https://github.com/isearchxsolve/emergentsh_latest/settings/access
16. [ ] https://github.com/isearchxsolve/frontend/settings/access
17. [ ] https://github.com/isearchxsolve/god_ai_scripts/settings/access
18. [ ] https://github.com/isearchxsolve/guardian_app/settings/access
19. [ ] https://github.com/isearchxsolve/gumroad-products/settings/access
20. [ ] https://github.com/isearchxsolve/hsf/settings/access
21. [ ] https://github.com/isearchxsolve/idea-terminal-engine/settings/access
22. [ ] https://github.com/isearchxsolve/ideation_to_prototype/settings/access
23. [ ] https://github.com/isearchxsolve/ikon_agent-main/settings/access
24. [ ] https://github.com/isearchxsolve/kdp-polished/settings/access
25. [ ] https://github.com/isearchxsolve/lasthelp/settings/access
26. [ ] https://github.com/isearchxsolve/lateststablecode/settings/access
27. [ ] https://github.com/isearchxsolve/nemo_test/settings/access
28. [ ] https://github.com/isearchxsolve/neon_unified/settings/access
29. [ ] https://github.com/isearchxsolve/oiioii_clone/settings/access
30. [ ] https://github.com/isearchxsolve/oiioii_clone2/settings/access
31. [ ] https://github.com/isearchxsolve/oiioii_clone3/settings/access
32. [ ] https://github.com/isearchxsolve/oiioii_clone_final/settings/access
33. [ ] https://github.com/isearchxsolve/oiioii_clone_final2/settings/access
34. [ ] https://github.com/isearchxsolve/oiioii_clone_final3/settings/access
35. [ ] https://github.com/isearchxsolve/oiioii_clone_full/settings/access
36. [ ] https://github.com/isearchxsolve/oiioii_clone_gen/settings/access
37. [ ] https://github.com/isearchxsolve/oioi/settings/access
38. [ ] https://github.com/isearchxsolve/omega/settings/access
39. [ ] https://github.com/isearchxsolve/omniroute-monetizer/settings/access
40. [ ] https://github.com/isearchxsolve/omniroute_dashboard/settings/access
41. [ ] https://github.com/isearchxsolve/scratch/settings/access
42. [ ] https://github.com/isearchxsolve/screen_guard_final/settings/access
43. [ ] https://github.com/isearchxsolve/solana-auto-trader-live/settings/access
44. [ ] https://github.com/isearchxsolve/stabletcode/settings/access
45. [ ] https://github.com/isearchxsolve/test_coding_agent/settings/access
46. [ ] https://github.com/isearchxsolve/the-beholder-project/settings/access
47. [ ] https://github.com/isearchxsolve/timeofmylife/settings/access
48. [ ] https://github.com/isearchxsolve/voice_agent_avatar/settings/access
49. [ ] https://github.com/isearchxsolve/war-pipe/settings/access

---

## After inviting — verify from the terminal (one command):

```powershell
python -c "import json,subprocess; repos=[l.strip() for l in open(r'D:\anonym\war-log\corpus-final.json').read() if False] or __import__('json').load(open(r'D:\anonym\war-log\corpus-final.json')).keys(); [print(r, subprocess.run(['gh','api',f'repos/isearchxsolve/{r}/invitations','--jq','.[] | select(.invitee.login==\"prafullprince\") | .permissions'],capture_output=True,text=True).stdout.strip() or 'NO-INVITE') for r in sorted(repos)]"
```

Simpler check for a single repo (run per repo or ask Kilo to run the sweep):

```powershell
gh api "repos/isearchxsolve/REPO_NAME/invitations" --jq ".[] | {invitee: .invitee.login, permissions}"
```

Each pending invitation must show `"permissions": "read"`. If any shows `"write"`, revoke:

```powershell
gh api -X DELETE "repos/isearchxsolve/REPO_NAME/invitations/INVITATION_ID"
```
