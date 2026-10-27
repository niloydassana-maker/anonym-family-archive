"""The declared-by-design gate, pinned at both edges.

Measured need (2026-10-27): Expensify/App#105153 was dispatched, a full Cline session ran,
and the verified result was ``action=blocked`` -- "documented by the repository's own
maintainer analysis as expected/by-design" (comment id 6447058391). Re-admitting the same
issue every discovery cycle spends a delivery run to relearn a written verdict.

Two edges matter, and the second is the dangerous one:

* A declaration only counts from a party that speaks for the repository. ``trusted()``
  refuses the issuing automation account (``MelvinBot``, author_association CONTRIBUTOR), so
  the programme's documented automation identities are honoured -- and only for that
  repository.
* ``Expected Behaviour`` is the heading every bug report carries, and it states the
  *opposite* of this verdict. It is never a marker. A gate that reads it rejects the entire
  funded backlog, which would look like progress while producing nothing.
"""
import unittest

from bounty_admission import declared_by_design, admit

HARD_TITLE = "[$250] Fix race condition in the report composer"
HARD_BODY = ("The composer sends a duplicate request when two tabs submit at once. "
             "See src/pages/Report/ReportComposer.tsx and the useSubmit hook.")

# The real declaring sentence, read live from
# repos/Expensify/App/issues/105153/comments (id 6447058391, 2026-10-27T16:09:17Z).
DECLARATION = ("**Root Cause:** This works as designed. It is not a bug. Turning on "
               "\"Simulate failing network requests\" does not send a new search request.")


def repository(full_name="Expensify/App", owner="Expensify"):
    return {"owner": {"login": owner}, "full_name": full_name,
            "archived": False, "disabled": False}


def issue(title=HARD_TITLE, body=HARD_BODY, labels=(), url="https://github.com/Expensify/App/issues/1"):
    return {"title": title, "body": body, "state": "open", "html_url": url,
            "labels": [{"name": name} for name in labels]}


def attestation():
    return {"user": {"login": "melvin-bot[bot]"}, "author_association": "NONE",
            "html_url": "https://github.com/Expensify/App/issues/1#issuecomment-1",
            "body": "Job added to Upwork: https://www.upwork.com/jobs/~022108002387844305757",
            "created_at": "2026-10-27T00:00:00Z"}


def comment(body, login="MelvinBot", association="CONTRIBUTOR", number=2):
    return {"user": {"login": login}, "author_association": association, "body": body,
            "html_url": f"https://github.com/Expensify/App/issues/1#issuecomment-{number}",
            "created_at": "2026-10-27T16:09:17Z"}


def context(comments=(), labels=(), repo="Expensify/App", owner="Expensify"):
    return {"repo": repo, "issue_number": 1, "repository": repository(repo, owner),
            "issue": issue(labels=labels), "comments": [attestation(), *comments],
            "complete_comments": True, "fetched_at": "unit fixture"}


class DeclarationIsReadTests(unittest.TestCase):
    def test_documented_automation_declaration_is_read(self):
        verdict = declared_by_design(context([comment(DECLARATION)]))
        self.assertEqual(verdict["verdict"], "BY_DESIGN")
        self.assertEqual(verdict["authority"], "MelvinBot")
        self.assertIn("works as designed", verdict["quote"])
        self.assertTrue(verdict["source_url"].endswith("#issuecomment-2"))

    def test_admission_refuses_the_declared_behaviour(self):
        proof, reason = admit(context([comment(DECLARATION)]))
        self.assertIsNone(proof)
        self.assertEqual(reason, "REPORTED_BEHAVIOUR_DECLARED_BY_DESIGN")

    def test_maintainer_association_declaration_is_read(self):
        verdict = declared_by_design(context(
            [comment("Closing this: the banner behaviour is by design.", login="maintainer",
                     association="MEMBER", number=3)]))
        self.assertEqual(verdict["authority"], "maintainer")

    def test_repository_owner_declaration_is_read(self):
        verdict = declared_by_design(context(
            [comment("Won't fix - no code change is warranted here.", login="Expensify",
                     association="NONE", number=4)]))
        self.assertIsNotNone(verdict)

    def test_quote_is_the_declaring_line_not_the_whole_comment(self):
        long_tail = "\n".join("line %d of unrelated analysis" % index for index in range(60))
        verdict = declared_by_design(context([comment(DECLARATION + "\n" + long_tail)]))
        self.assertLess(len(verdict["quote"]), 260)
        self.assertNotIn("line 0 of unrelated analysis", verdict["quote"])

    def test_declaration_returns_the_reason_helper_only_on_declaration(self):
        self.assertEqual(admit(context([comment(DECLARATION)]))[1],
                         "REPORTED_BEHAVIOUR_DECLARED_BY_DESIGN")
        self.assertEqual(admit(context())[1], "")


class AuthorityIsRequiredTests(unittest.TestCase):
    def test_untrusted_stranger_agreement_cannot_establish_it(self):
        """The measured payload had a stranger (author_association NONE) merely agreeing."""
        proof, reason = admit(context([
            comment("Agreed, this is not a bug - works as designed.", login="camesenin",
                    association="NONE", number=5)]))
        self.assertIsNotNone(proof)
        self.assertEqual(reason, "")

    def test_automation_login_is_scoped_to_its_own_repository(self):
        """The same login on an unrelated repository establishes nothing."""
        verdict = declared_by_design(context(
            [comment(DECLARATION)], repo="Other/Project", owner="Other"))
        self.assertIsNone(verdict)

    def test_a_foreign_bot_is_not_an_authority(self):
        verdict = declared_by_design(context([
            comment(DECLARATION, login="helpful-bot[bot]", association="NONE", number=6)]))
        self.assertIsNone(verdict)


class FalsePositiveTests(unittest.TestCase):
    """The edge that would silently empty the funded backlog."""

    def test_expected_behaviour_heading_is_never_a_marker(self):
        # Every bug report carries this heading and it states the opposite of this verdict.
        # Written by an authority on purpose: authority alone must not convert a routine
        # report into a declaration, or the gate empties the funded backlog.
        report = ("Steps: open Settings, toggle the network simulator.\n\n"
                  "Expected Behaviour\nThe refresh banner should reappear.\n\n"
                  "Actual Behaviour\nIt does not.")
        proof, reason = admit(context())
        self.assertIsNotNone(proof, reason)
        self.assertIsNone(declared_by_design(context([comment(report)])))

    def test_ordinary_analysis_that_mentions_design_is_not_a_declaration(self):
        analysis = ("The composer design routes both tabs through useSubmit, so the "
                    "second request races the first. Expected Behaviour is one request.")
        verdict = declared_by_design(context([
            comment(analysis, login="maintainer", association="MEMBER", number=7)]))
        self.assertIsNone(verdict)

    def test_maintainer_naming_the_intended_behaviour_is_not_a_declaration(self):
        verdict = declared_by_design(context([
            comment("The intended behaviour is that the banner refreshes after a failed "
                    "request; it is not doing that.", login="maintainer",
                    association="MEMBER", number=8)]))
        self.assertIsNone(verdict)

    def test_a_normal_funded_report_is_admitted_untouched(self):
        proof, reason = admit(context())
        self.assertIsNotNone(proof, reason)
        self.assertEqual(proof["funding"]["amount"], "250")
        self.assertEqual(proof["funding"]["payer"], "melvin-bot[bot]")


class WithdrawalTests(unittest.TestCase):
    def test_later_authoritative_bug_statement_clears_the_verdict(self):
        proof, reason = admit(context([
            comment(DECLARATION, number=9),
            comment("This is a real bug after all - reopening.", login="maintainer",
                    association="MEMBER", number=10)]))
        self.assertIsNotNone(proof, reason)

    def test_explicit_withdrawal_of_the_by_design_call_clears_it(self):
        verdict = declared_by_design(context([
            comment(DECLARATION, number=11),
            comment("Correction: this is not by design.", login="MelvinBot", number=12)]))
        self.assertIsNone(verdict)

    def test_a_later_declaration_overrides_an_earlier_bug_statement(self):
        verdict = declared_by_design(context([
            comment("This is a real bug.", login="maintainer", association="MEMBER", number=13),
            comment(DECLARATION, number=14)]))
        self.assertIsNotNone(verdict)


class LabelTests(unittest.TestCase):
    def test_a_by_design_label_rejects_when_no_comment_settles_it(self):
        verdict = declared_by_design(context(labels=["wontfix"]))
        self.assertEqual(verdict["author_association"], "LABEL")
        self.assertEqual(verdict["quote"], "labels: wontfix")
        self.assertIsNone(admit(context(labels=["wontfix"]))[0])

    def test_an_authoritative_bug_statement_beats_a_stale_label(self):
        proof, reason = admit(context([
            comment("This is a real bug, reopening.", login="maintainer",
                    association="MEMBER", number=15)], labels=["wontfix"]))
        self.assertIsNotNone(proof, reason)

    def test_unrelated_labels_do_not_reject(self):
        proof, reason = admit(context(labels=["bug", "External", "Internal"]))
        self.assertIsNotNone(proof, reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
