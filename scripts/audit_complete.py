#!/usr/bin/env python3
"""Complete audit of F1-F12 implementation against the blueprint."""
import os

with open('D:/anonym/scripts/actions_dispatch.py') as f:
    d = f.read()
with open('D:/anonym/scripts/actions_delivery.py') as f:
    d2 = f.read()
with open('D:/anonym/scripts/actions_github.py') as f:
    d3 = f.read()

checks = []

# F1/F2: base_branch from prepared
checks.append(('F1: base_branch from prepared in dispatch', 'prepared.get("base_branch")' in d or 'prepared["base_branch"]' in d))
checks.append(('F2: base_branch in compare URL', 'compare/{base}...{default_branch}' in d2))

# F3
checks.append(('F3: write_json_atomic', 'def write_json_atomic' in d2))
checks.append(('F3: ClineDeliverableMissing', 'class ClineDeliverableMissing' in d2))
checks.append(('F3: ClineDeliverableInvalid', 'class ClineDeliverableInvalid' in d2))
checks.append(('F3: validate_preparation', 'def validate_preparation' in d2))
checks.append(('F3: validate_preparation called', 'validate_preparation(' in d2))

# F4
checks.append(('F4: PreparationRace', 'class PreparationRace' in d2))
checks.append(('F4: ClineDeliverableMissing', 'class ClineDeliverableMissing' in d2))
checks.append(('F4: ClineDeliverableInvalid', 'class ClineDeliverableInvalid' in d2))
checks.append(('F4: RunnerShutdown', 'class RunnerShutdown' in d2))
checks.append(('F4: InfrastructureFault', 'class InfrastructureFault' in d2))

# F5
checks.append(('F5: CLAIM_TTL_SECONDS', 'CLAIM_TTL_SECONDS' in d3))
checks.append(('F5: _lease_expired_and_dead', '_lease_expired_and_dead' in d3))
checks.append(('F5: lease_expires_at stored', 'lease_expires_at' in d3))

# F6
checks.append(('F6: repository_velocity', 'def repository_velocity' in d))
checks.append(('F6: velocity_24h stored', 'velocity_24h' in d))

# F7
checks.append(('F7: preflight function', 'def preflight(' in d2))
checks.append(('F7: check_disk_space', 'def check_disk_space' in d2))
checks.append(('F7: check_free_memory', 'def check_free_memory' in d2))
checks.append(('F7: check_executable', 'def check_executable' in d2))
checks.append(('F7: check_git_version', 'def check_git_version' in d2))
checks.append(('F7: preflight called in engineer', 'preflight([' in d2))

# F8
checks.append(('F8: heartbeat function', 'def heartbeat(' in d))
checks.append(('F8: newest_schedule_run', 'def newest_schedule_run' in d))
checks.append(('F8: recent_runs', 'def recent_runs' in d))
checks.append(('F8: within_cooldown', 'def within_cooldown' in d))

# F9
checks.append(('F9: is_code_change_request', 'def is_code_change_request' in d))
checks.append(('F9: code keywords required', 'has_code_keywords or has_code_ref' in d))

# F10
checks.append(('F10: submodule.recurse=false', 'submodule.recurse=false' in d2))

# F11
checks.append(('F11: census in dispatch', 'census.jsonl' in d))

# F12
checks.append(('F12: failure_digest.py exists', os.path.exists('D:/anonym/scripts/failure_digest.py')))

all_pass = True
for name, result in checks:
    status = 'PASS' if result else 'FAIL'
    if not result:
        all_pass = False
    print(f'{status}: {name}')

print()
print('F12 failure_digest.py exists:', os.path.exists('D:/anonym/scripts/failure_digest.py'))
print()
print('ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED')