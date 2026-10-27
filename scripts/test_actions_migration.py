"""Deterministic unit fixtures; these are not live delivery receipts."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from actions_dispatch import discover, query_window
from actions_github import GitHub, GitHubError, StateStore, task_id
from actions_reconcile import classify_checks
from actions_release import (git, manifest, protect_baseline_tests, regression_proof,
                             require_commands, safe_path, status_paths, validate_plan_contract, restore_checkpoint)
from bounty_admission import admit, amounts, competition


def context():
    return {"repo": "owner/project", "issue_number": 7, "title": "Parser race condition", "body": "Fix src/parser.py", "complete_comments": True,
            "repository": {"owner": {"login": "owner"}}, "fetched_at": "unit fixture",
            "issue": {"title": "Parser race condition", "body": "Fix deadlock in src/parser.py. Bounty $500.",
                      "state": "open", "html_url": "https://github.com/owner/project/issues/7",
                      "user": {"login": "owner"}, "author_association": "OWNER"}, "comments": []}


class AdmissionTests(unittest.TestCase):
    def test_real_issuer_amount_and_hard_scope(self):
        proof, reason = admit(context())
        self.assertEqual(reason, "")
        self.assertEqual(proof["funding"]["amount"], "500")

    def test_comment_offer_and_title_offer(self):
        c = context()
        c["comments"] = [{**c["issue"], "body": "/bounty $1200"}]
        c["issue"]["body"] = "Fix parser deadlock in src/parser.py"
        self.assertEqual(admit(c)[0]["funding"]["amount"], "1200")
        c["comments"] = []
        c["issue"]["title"] = "[Bounty $100] parser regression"
        self.assertIsNotNone(admit(c)[0])

    def test_funding_match_offsets_survive_long_code_blocks_and_repeated_price(self):
        c = context()
        c["issue"]["title"] = "[$750] memory performance regression"
        c["issue"]["body"] = ("Fix src/parser.py\n" + "x" * 1000 + "\n```sh\n" + "code\n" * 200 +
                               "```\n" + "z" * 1000 + "\nBounty: $750 USD paid by maintainers")
        self.assertEqual(admit(c)[0]["funding"]["amount"], "750")

    def test_no_phantom_amount_from_severity(self):
        c = context()
        c["issue"]["body"] = "P0 parser crash in src/parser.py; urgent bounty"
        self.assertIsNone(admit(c)[0])

    def test_payee_and_untrusted_offer(self):
        for body, login, association in [("Bounty $500; payout wallet", "owner", "OWNER"),
                                          ("Bounty $500", "outsider", "NONE")]:
            c = context()
            c["issue"].update(body="Parser crash in src/parser.py " + body,
                               user={"login": login}, author_association=association)
            self.assertIsNone(admit(c)[0])

    def test_withdrawal_overrides_previous_offer(self):
        c = context()
        c["comments"] = [{**c["issue"], "body": "Withdraw the bounty; no longer offering"}]
        self.assertIsNone(admit(c)[0])

    def test_metrics_code_strikethrough_not_currency(self):
        for body in ["$500$ micrometers", "~~$500~~", "```\n$500\n```", "$500 TVL", "$500 pool"]:
            self.assertEqual(list(amounts(body)), [])

    def test_missing_comments_and_mirrors(self):
        c = context()
        c["complete_comments"] = False
        self.assertEqual(admit(c)[1], "INCOMPLETE_COMMENTS")
        c = context()
        c["issue"]["title"] = "Daily digest"
        self.assertIsNone(admit(c)[0])

    def test_crypto_requires_observed_quote(self):
        c = context()
        c["issue"]["body"] = "Parser deadlock src/parser.py bounty 2 SOL"
        self.assertIsNone(admit(c)[0])
        self.assertIsNotNone(admit(c, quote=lambda _: {"usd_rate": "60", "source_url": "unit fixture"})[0])

    def test_component_not_invented_from_url(self):
        c = context()
        c["issue"].update(title="Crash bounty $500", body="Crash https://example.org/a/file.py")
        self.assertIsNone(admit(c)[0])


class TransportTests(unittest.TestCase):
    def test_complete_search_pagination(self):
        calls = []
        def get(endpoint):
            calls.append(endpoint)
            return {"items": [dict(number=i) for i in range(100 if len(calls) == 1 else 37)],
                    "total_count": 137, "incomplete_results": False}
        rows, total = query_window(SimpleNamespace(api=get), "bounty")
        self.assertEqual((len(rows), total, len(calls)), (137, 137, 2))

    def test_saturated_search_partitions_before_hydration(self):
        rows, total = query_window(SimpleNamespace(api=lambda _: {"items": [{}] * 100, "total_count": 1500}), "bounty")
        self.assertEqual((rows, total), ([], 1500))

    def test_incomplete_is_error_not_zero(self):
        with self.assertRaises(GitHubError):
            query_window(SimpleNamespace(api=lambda _: {"items": [], "incomplete_results": True}), "bounty")

    def test_full_issue_body_and_all_comments(self):
        api = GitHub()
        issue = {"title": "fixture", "body": "x" * 50000, "comments": 101}
        def get(url, **kwargs):
            if "/comments?" in url:
                self.assertTrue(kwargs["paginate"])
                return [[{}] * 99, [{}] * 2]
            return issue if "/issues/" in url else {"default_branch": "main"}
        with patch.object(api, "api", side_effect=get):
            result = api.issue_context("owner/repo", 1)
        self.assertTrue(result["complete_comments"])
        self.assertEqual(len(result["body"]), 50000)

    def test_stale_rest_counter_needs_independent_visible_count_and_last_id(self):
        api = GitHub()
        issue = {"title": "fixture", "body": "full context", "comments": 3}
        def get(url, *args, **kwargs):
            if url == "graphql":
                return {"data": {"repository": {"issue": {"comments": {
                    "totalCount": 2, "nodes": [{"databaseId": 12}]}}}}}
            if "/comments?" in url:
                return [[{"id": 11}, {"id": 12}]]
            return issue if "/issues/" in url else {}
        with patch.object(api, "api", side_effect=get):
            result = api.issue_context("owner/repo", 1)
        self.assertTrue(result["complete_comments"])
        self.assertEqual(result["comment_count_evidence"]["rest_reported"], 3)
        self.assertEqual(result["comment_count_evidence"]["graphql_visible"], 2)

    def test_unsafe_task_identity_rejected(self):
        for repo, number in [("a/b;echo", 1), ("a/b", "$(shell)"), ("a/b", True)]:
            with self.assertRaises(ValueError):
                task_id(repo, number)

    def test_hydration_budget_keeps_every_unprocessed_search_result(self):
        items = [{"repository_url": "https://api.github.com/repos/owner/project", "number": n,
                  "updated_at": "fixture"} for n in range(1, 102)]
        def get(endpoint):
            if "search/issues?" in endpoint:
                rows = items[:30] if "per_page=30" in endpoint else items[100:] if "&page=2" in endpoint else items[:100]
                return {"items": rows, "total_count": 101}
            raise AssertionError(endpoint)
        fake = SimpleNamespace(api=get, issue_context=lambda repo, number: context(), pages=lambda *a, **k: [])
        import sqlite3
        with tempfile.TemporaryDirectory() as folder, patch("actions_dispatch.GitHub", return_value=fake):
            with patch("builtins.print"):
                discover(["normal"], queries_per_lane=1, state_dir=folder)
            with sqlite3.connect(Path(folder) / "discovery.sqlite3") as con:
                counts = dict(con.execute("SELECT status,count(*) FROM pending GROUP BY status"))
            con.close()
            self.assertEqual(counts, {"checked": 60, "pending": 41})
            con = sqlite3.connect(Path(folder) / "discovery.sqlite3")
            con.execute("UPDATE metadata SET value='previous broken policy' WHERE name='admission_policy'")
            con.execute("UPDATE pending SET status='checked'")
            con.commit()
            con.close()
            with patch("builtins.print"):
                discover(["normal"], queries_per_lane=1, state_dir=folder)
            con = sqlite3.connect(Path(folder) / "discovery.sqlite3")
            counts = dict(con.execute("SELECT status,count(*) FROM pending GROUP BY status"))
            con.close()
            self.assertEqual(counts, {"checked": 60, "pending": 41})

    def test_current_open_competition(self):
        pr = {"title": "Fix #7", "body": "", "head": {"ref": "fix/7", "sha": "a", "repo": None}, "html_url": "unit fixture"}
        api = SimpleNamespace(pages=lambda *a, **k: [pr])
        with self.assertRaisesRegex(ValueError, "Competing"):
            competition(api, "owner/project", 7)

    def test_ownership_and_attempt_bounds(self):
        store = StateStore()
        old = {"status": "CLAIMED", "owner": "1:1", "attempt": 1}
        store.mutate = lambda identity, change: change(old)
        store.api = SimpleNamespace(api=lambda _: {"status": "in_progress"})
        with self.assertRaisesRegex(ValueError, "live Actions"):
            store.claim("owner/project", 7, "2:1", "run", "sha")
        old.update(status="FAILED", attempt=3)
        with self.assertRaisesRegex(ValueError, "exhausted"):
            store.claim("owner/project", 7, "2:1", "run", "sha")

    def test_remote_no_checks_is_not_passed(self):
        api = SimpleNamespace(api=lambda _: {"check_runs": []}, pages=lambda _: [])
        self.assertEqual(classify_checks(api, "owner/project", "head")["state"], "NO_REMOTE_CHECKS")

    def test_later_rerun_supersedes_old_failure(self):
        rows = [{"id": 1, "name": "native", "status": "completed", "conclusion": "failure"},
                {"id": 2, "name": "native", "status": "completed", "conclusion": "success"}]
        api = SimpleNamespace(api=lambda _: {"check_runs": rows}, pages=lambda _: [])
        self.assertEqual(classify_checks(api, "owner/project", "head")["state"], "PASSED")

    def test_maintainer_approval_is_pending_not_a_code_repair(self):
        rows = [{"id": 1, "name": "native", "status": "completed", "conclusion": "action_required"}]
        api = SimpleNamespace(api=lambda _: {"check_runs": rows}, pages=lambda _: [])
        proof = classify_checks(api, "owner/project", "head")
        self.assertEqual(proof["state"], "PENDING")
        self.assertEqual(proof["failures"], [])


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "fixture@example.invalid")
        git(self.root, "config", "user.name", "Unit fixture")
        git(self.root, "config", "core.autocrlf", "false")
        (self.root / "product.py").write_text("def value(): return 0\n")
        (self.root / "tests").mkdir()
        (self.root / "tests/master.py").write_text("# immutable fixture\n")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "unit baseline")
        self.base = git(self.root, "rev-parse", "HEAD").stdout.decode().strip()

    def tearDown(self):
        self.temp.cleanup()

    def test_new_test_directory_preserved(self):
        p = self.root / "tests/regression/new case.py"
        p.parent.mkdir()
        p.write_text("# companion")
        self.assertEqual(status_paths(self.root), ["tests/regression/new case.py"])

    @unittest.skipIf(os.name == "nt", "Windows filesystem prohibits newline names")
    def test_newline_path_roundtrip(self):
        (self.root / "odd\nname.py").write_text("# companion")
        self.assertEqual(status_paths(self.root), ["odd\nname.py"])

    def test_rename_and_deletion_include_sources(self):
        git(self.root, "mv", "product.py", "renamed.py")
        self.assertEqual(status_paths(self.root), ["product.py", "renamed.py"])

    def test_master_tests_are_immutable(self):
        with self.assertRaisesRegex(ValueError, "master test"):
            protect_baseline_tests(self.root, self.base, ["tests/master.py"])

    def test_git_object_script_protection_without_checkout(self):
        (self.root / "package.json").write_text(json.dumps({"scripts": {"test": "native-test"}}))
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "unit manifest")
        base = git(self.root, "rev-parse", "HEAD").stdout.decode().strip()
        (self.root / "package.json").write_text(json.dumps({"scripts": {"test": "echo pass"}}))
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "tamper fixture")
        head = git(self.root, "rev-parse", "HEAD").stdout.decode().strip()
        (self.root / "package.json").unlink()
        with self.assertRaisesRegex(ValueError, "verification script"):
            protect_baseline_tests(self.root, base, ["package.json"], head_sha=head)

    def test_paths_cannot_escape(self):
        for name in ("../secret", "/absolute", ".git/config", ".github/workflows/ci.yml"):
            with self.assertRaises(ValueError):
                safe_path(self.root, name)

    def test_real_red_to_green_runs_actual_source(self):
        (self.root / "product.py").write_text("def value(): return 1\n")
        test = self.root / "tests/regression.py"
        test.write_text("from product import value\nassert value() == 1, 'specific regression fixture assertion'\n")
        before = manifest(self.root, status_paths(self.root))
        def execute(argv):
            result = subprocess.run(argv, cwd=self.root, text=True, capture_output=True,
                                    env={**os.environ, "PYTHONPATH": str(self.root), "PYTHONDONTWRITEBYTECODE": "1"}, timeout=10)
            return SimpleNamespace(stdout=result.stdout, stderr=result.stderr, exit_code=result.returncode)
        proof = regression_proof(self.root, self.base, {"test_files": ["tests/regression.py"],
                "argv": [sys.executable, "-B", str(test)], "expected_failure": "specific regression fixture assertion"}, execute)
        self.assertNotEqual(proof["red_exit"], 0)
        self.assertEqual(proof["green_exit"], 0)
        self.assertEqual(manifest(self.root, status_paths(self.root)), before)

    def test_checkpoint_restores_real_tracked_and_new_companion_bytes(self):
        import zipfile
        (self.root / "product.py").write_text("def value(): return 1\n")
        patch_bytes = git(self.root, "diff", "--binary", "HEAD").stdout
        git(self.root, "restore", "product.py")
        with tempfile.TemporaryDirectory() as outside:
            archive = Path(outside) / "checkpoint.zip"
            with zipfile.ZipFile(archive, "w") as saved:
                saved.writestr("checkpoint.json", json.dumps({"schema": 1, "head_sha": self.base}))
                saved.writestr("tracked.patch", patch_bytes)
                saved.writestr("untracked/tests/new_companion.py", "# retained companion\n")
            receipt = restore_checkpoint(self.root, self.base, archive)
        self.assertEqual(receipt["status"], "RESTORED")
        self.assertEqual((self.root / "product.py").read_text(), "def value(): return 1\n")
        self.assertEqual((self.root / "tests/new_companion.py").read_text(), "# retained companion\n")

    def test_failed_or_warning_receipts_block(self):
        for code, output in [(1, ""), (0, "warning: unsafe"), (0, "npm warn unsupported engine"), (0, "4:4 warning unused variable"), (0, "0 errors, 2 warnings"), (0, "Ran 0 tests")]:
            with self.assertRaises(ValueError):
                require_commands([["native", "test"]], [{"argv": ["native", "test"], "exit_code": code, "stdout": output}])
        with self.assertRaises(ValueError):
            require_commands([["native", "test"]], [])

    def test_no_bypass_native_plan(self):
        for command in (["echo", "pass"], ["npm", "test", "--if-present"], ["sh", "-c", "run || true"]):
            plan = SimpleNamespace(builds=[command], baseline_tests=[["native", "test"]],
                                   final_tests=[["native", "test"]], linters=[["native", "lint"]])
            with self.assertRaises(ValueError):
                validate_plan_contract(plan)


if __name__ == "__main__":
    unittest.main(verbosity=2)
