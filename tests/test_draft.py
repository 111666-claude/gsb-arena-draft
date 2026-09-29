import random
import time
import unittest

from arenadraft.draft import Draft, DraftError, ban, resolve


class BanTest(unittest.TestCase):
    def test_ban_recorded(self):
        draft = Draft(["hero1", "hero2"])
        ban(draft, "a", "hero1", 0)
        self.assertEqual(draft.bans["a"], ["hero1"])

    def test_both_sides_have_lists(self):
        draft = Draft(["hero1"])
        self.assertEqual(sorted(draft.bans), ["a", "b"])

    def test_error_type(self):
        self.assertTrue(issubclass(DraftError, ValueError))

    def test_resolve_counts_bans(self):
        draft = Draft(["hero1", "hero2"])
        ban(draft, "a", "hero1", 0)
        ban(draft, "b", "hero2", 1)
        self.assertEqual(resolve(draft, 2), 2)


if __name__ == "__main__":
    unittest.main()


class DuplicateBanTest(unittest.TestCase):
    def test_same_side_duplicate_rejected(self):
        draft = Draft(["hero1", "hero2"], deadline=100, limit=2)
        ban(draft, "a", "hero1", 10)
        with self.assertRaises(DraftError):
            ban(draft, "a", "hero1", 20)

    def test_cross_side_duplicate_rejected(self):
        draft = Draft(["hero1", "hero2"], deadline=100)
        ban(draft, "a", "hero1", 10)
        with self.assertRaises(DraftError) as ctx:
            ban(draft, "b", "hero1", 20)
        self.assertIn("hero1", str(ctx.exception))

    def test_failed_duplicate_keeps_state(self):
        draft = Draft(["hero1", "hero2"], deadline=100)
        ban(draft, "a", "hero1", 10)
        try:
            ban(draft, "b", "hero1", 20)
        except DraftError:
            pass
        self.assertEqual(draft.bans, {"a": ["hero1"], "b": []})
        self.assertEqual(resolve(draft, 30), 1)


class TimeoutDefaultTest(unittest.TestCase):
    def test_both_sides_defaulted_after_deadline(self):
        draft = Draft(["hero1", "hero2", "hero3"], deadline=100)
        self.assertEqual(resolve(draft, 500), 2)
        self.assertEqual(draft.bans, {"a": ["hero1"], "b": ["hero2"]})

    def test_only_missing_side_defaulted(self):
        draft = Draft(["hero1", "hero2", "hero3"], deadline=100)
        ban(draft, "a", "hero3", 50)
        self.assertEqual(resolve(draft, 500), 2)
        self.assertEqual(draft.bans, {"a": ["hero3"], "b": ["hero1"]})

    def test_default_skips_already_banned(self):
        draft = Draft(["hero1", "hero2", "hero3", "hero4"], deadline=100)
        ban(draft, "a", "hero1", 50)
        ban(draft, "b", "hero2", 60)
        draft.limit = 2
        self.assertEqual(resolve(draft, 500), 4)
        self.assertEqual(draft.bans, {"a": ["hero1", "hero3"], "b": ["hero2", "hero4"]})

    def test_before_deadline_no_default(self):
        draft = Draft(["hero1", "hero2"], deadline=100)
        self.assertEqual(resolve(draft, 100), 0)
        self.assertEqual(draft.bans, {"a": [], "b": []})

    def test_late_submission_rejected(self):
        draft = Draft(["hero1", "hero2"], deadline=100)
        with self.assertRaises(DraftError):
            ban(draft, "a", "hero1", 101)
        self.assertEqual(draft.bans, {"a": [], "b": []})

    def test_resolve_idempotent(self):
        draft = Draft(["hero1", "hero2", "hero3"], deadline=100)
        first = resolve(draft, 500)
        snapshot = {side: list(items) for side, items in draft.bans.items()}
        second = resolve(draft, 600)
        self.assertEqual(first, second)
        self.assertEqual(draft.bans, snapshot)


class PoolValidationTest(unittest.TestCase):
    def test_hero_not_in_pool_rejected(self):
        draft = Draft(["hero1", "hero2"], deadline=100)
        with self.assertRaises(DraftError) as ctx:
            ban(draft, "a", "ghost", 10)
        self.assertIn("ghost", str(ctx.exception))

    def test_invalid_hero_keeps_state(self):
        draft = Draft(["hero1", "hero2"], deadline=100)
        ban(draft, "a", "hero1", 10)
        try:
            ban(draft, "b", "ghost", 20)
        except DraftError:
            pass
        self.assertEqual(draft.bans, {"a": ["hero1"], "b": []})

    def test_unknown_side_rejected(self):
        draft = Draft(["hero1"], deadline=100)
        with self.assertRaises(DraftError):
            ban(draft, "c", "hero1", 10)


class InvariantTest(unittest.TestCase):
    def test_per_side_limit_enforced(self):
        draft = Draft(["hero1", "hero2", "hero3"], deadline=100, limit=1)
        ban(draft, "a", "hero1", 10)
        with self.assertRaises(DraftError):
            ban(draft, "a", "hero2", 20)
        self.assertLessEqual(len(draft.bans["a"]), 1)

    def test_bans_always_unique(self):
        draft = Draft(["h%d" % i for i in range(10)], deadline=50, limit=3)
        for now in range(10):
            for side in ("a", "b"):
                for hero in draft.pool:
                    try:
                        ban(draft, side, hero, now)
                    except DraftError:
                        pass
        resolve(draft, 100)
        all_bans = draft.bans["a"] + draft.bans["b"]
        self.assertEqual(len(all_bans), len(set(all_bans)))
        for side in ("a", "b"):
            self.assertLessEqual(len(draft.bans[side]), draft.limit)


class ScaleTest(unittest.TestCase):
    def test_100k_submissions_under_one_second(self):
        pool = ["h%d" % i for i in range(200)]
        draft = Draft(pool, deadline=10 ** 9, limit=100)
        start = time.monotonic()
        for i in range(100000):
            try:
                ban(draft, "ab"[i % 2], pool[i % 200], i)
            except DraftError:
                pass
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 1.0)
        self.assertEqual(resolve(draft, 10 ** 9), 200)


class ReferenceImplementation:
    """去重校验 + 超时默认的朴素参考实现，用于逐步对照。"""

    def __init__(self, pool, deadline, limit):
        self.pool = list(pool)
        self.deadline = deadline
        self.limit = limit
        self.bans = {"a": [], "b": []}

    def _timed_out(self, now):
        return self.deadline > 0 and now > self.deadline

    def ban(self, side, hero, now):
        if self._timed_out(now):
            raise DraftError("too late: %r" % hero)
        if hero not in self.pool:
            raise DraftError("not in pool: %r" % hero)
        if hero in self.bans["a"] or hero in self.bans["b"]:
            raise DraftError("already banned: %r" % hero)
        if len(self.bans[side]) >= self.limit:
            raise DraftError("limit reached: %r" % hero)
        self.bans[side].append(hero)

    def resolve(self, now):
        if self._timed_out(now):
            for side in ("a", "b"):
                while len(self.bans[side]) < self.limit:
                    banned = self.bans["a"] + self.bans["b"]
                    candidates = [h for h in self.pool if h not in banned]
                    if not candidates:
                        break
                    self.bans[side].append(candidates[0])
        return len(self.bans["a"]) + len(self.bans["b"])


class DifferentialTest(unittest.TestCase):
    def test_matches_reference_on_random_sequences(self):
        rng = random.Random(20260930)
        diffs = 0
        for case in range(200):
            pool = ["h%d" % i for i in range(rng.randint(2, 12))]
            deadline = rng.choice([0, 5, 20, 100])
            limit = rng.randint(1, 3)
            draft = Draft(pool, deadline=deadline, limit=limit)
            ref = ReferenceImplementation(pool, deadline, limit)
            heroes = pool + ["ghost%d" % i for i in range(3)]
            for step in range(40):
                side = rng.choice(["a", "b"])
                hero = rng.choice(heroes + (pool[:1] if pool else []))
                now = rng.randint(0, 150)
                err_d = err_r = None
                try:
                    ban(draft, side, hero, now)
                except DraftError as exc:
                    err_d = exc
                try:
                    ref.ban(side, hero, now)
                except DraftError as exc:
                    err_r = exc
                if (err_d is None) != (err_r is None) or draft.bans != ref.bans:
                    diffs += 1
                if rng.random() < 0.3:
                    now_r = rng.randint(0, 200)
                    if resolve(draft, now_r) != ref.resolve(now_r) or draft.bans != ref.bans:
                        diffs += 1
            final_now = rng.randint(0, 200)
            if resolve(draft, final_now) != ref.resolve(final_now) or draft.bans != ref.bans:
                diffs += 1
        self.assertEqual(diffs, 0)
