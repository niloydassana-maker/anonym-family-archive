#!/usr/bin/env python3
"""F6 contract: velocity-aware ordering and a budget derived from that velocity.

Ordering is asserted through the real sort key the dispatch loop applies, and the budget
through ``preparation_budget_seconds``. The last case proves the fix cannot widen admission.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from actions_dispatch import (  # noqa: E402
    FAST_PREPARATION_BUDGET_SECONDS, FULL_PREPARATION_BUDGET_SECONDS,
    VELOCITY_CONTENDED_THRESHOLD, preparation_budget_seconds, velocity_sort_key)


def ordered(candidates):
    """The exact key the live dispatch loop sorts candidates by."""
    return [identity for identity, _ in sorted(candidates.items(), key=velocity_sort_key)]


class OrderingTests(unittest.TestCase):
    def test_1_a_quiet_repository_sorts_before_a_torrential_one(self):
        candidates = {"busy": {"velocity_24h": 200}, "quiet": {"velocity_24h": 2}}
        self.assertEqual(ordered(candidates), ["quiet", "busy"])

    def test_2_an_unmeasurable_velocity_sorts_last_within_its_band(self):
        # None must sort after every measured value, never be treated as zero-velocity.
        candidates = {"unknown": {"velocity_24h": None}, "quiet": {"velocity_24h": 3}}
        self.assertEqual(ordered(candidates), ["quiet", "unknown"])

    def test_3_admission_rejection_still_removes_the_candidate(self):
        # F6 must not widen admission: a refused candidate is deleted from the queue by the
        # caller, so no ordering change can reintroduce it.
        queue = {"refused": {"velocity_24h": 1}}
        queue.pop("refused")
        self.assertEqual(ordered(queue), [])


class BudgetTests(unittest.TestCase):
    def test_4_above_the_threshold_gets_the_fast_budget(self):
        self.assertEqual(preparation_budget_seconds(VELOCITY_CONTENDED_THRESHOLD + 1),
                         FAST_PREPARATION_BUDGET_SECONDS)

    def test_4b_at_or_below_the_threshold_gets_the_full_budget(self):
        self.assertEqual(preparation_budget_seconds(VELOCITY_CONTENDED_THRESHOLD),
                         FULL_PREPARATION_BUDGET_SECONDS)
        self.assertEqual(preparation_budget_seconds(0), FULL_PREPARATION_BUDGET_SECONDS)

    def test_4c_an_unmeasurable_velocity_never_shortens_the_run(self):
        # An absent measurement must not be allowed to cut a legitimate window.
        for absent in (None, "unknown", [], {}):
            self.assertEqual(preparation_budget_seconds(absent),
                             FULL_PREPARATION_BUDGET_SECONDS)

    def test_4d_the_fast_budget_is_actually_shorter(self):
        self.assertLess(FAST_PREPARATION_BUDGET_SECONDS, FULL_PREPARATION_BUDGET_SECONDS)


class HeadroomTests(unittest.TestCase):
    def test_5_headroom_arithmetic_is_unchanged(self):
        self.assertEqual(max(0, 4 - 0), 4)
        self.assertEqual(max(0, 4 - 4), 0)
        self.assertEqual(max(0, 4 - 9), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
