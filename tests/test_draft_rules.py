import random
import time
import unittest

from arenadraft.draft import Draft, DraftError, ban, resolve


class DuplicateBanTest(unittest.TestCase):
    def test_same_hero_banned_twice_raises(self):
        draft = Draft(["hero1", "hero2"], deadline=100)
        ban(draft, "a", "hero1", 10)
        with self.assertRaises(DraftError):
            ban(draft, "b", "hero1", 20)
        self.assertEqual(draft.bans, {"a": ["hero1"], "b": []})

    def test_same_side_duplicate_raises(self):
        draft = Draft(["hero1", "hero2"], deadline=100, limit=2)
        ban(draft, "a", "hero1", 10)
        with self.assertRaises(DraftError):
            ban(draft, "a", "hero1", 20)
        self.assertEqual(draft.bans["a"], ["hero1"])


class PoolValidationTest(unittest.TestCase):
    def test_hero_not_in_pool_raises_and_keeps_state(self):
        draft = Draft(["hero1", "hero2"], deadline=100)
        ban(draft, "a", "hero1", 10)
        with self.assertRaises(DraftError):
            ban(draft, "b", "ghost", 20)
        self.assertEqual(draft.bans, {"a": ["hero1"], "b": []})

    def test_error_is_value_error(self):
        draft = Draft(["hero1"], deadline=100)
        with self.assertRaises(ValueError):
            ban(draft, "a", "ghost", 10)


class TimeoutDefaultTest(unittest.TestCase):
    def test_resolve_fills_missing_sides_after_deadline(self):
        draft = Draft(["hero1", "hero2", "hero3"], deadline=100)
        self.assertEqual(resolve(draft, 500), 2)
        self.assertEqual(draft.bans, {"a": ["hero1"], "b": ["hero2"]})

    def test_default_skips_already_banned(self):
        draft = Draft(["hero1", "hero2", "hero3"], deadline=100)
        ban(draft, "a", "hero1", 10)
        self.assertEqual(resolve(draft, 500), 2)
        self.assertEqual(draft.bans, {"a": ["hero1"], "b": ["hero2"]})

    def test_late_submission_raises_and_defaults_applied(self):
        draft = Draft(["hero1", "hero2"], deadline=100)
        with self.assertRaises(DraftError):
            ban(draft, "a", "hero2", 500)
        self.assertEqual(resolve(draft, 600), 2)

    def test_resolve_is_idempotent(self):
        draft = Draft(["hero1", "hero2", "hero3"], deadline=100)
        first = resolve(draft, 500)
        snapshot = {side: list(items) for side, items in draft.bans.items()}
        self.assertEqual(resolve(draft, 600), first)
        self.assertEqual(draft.bans, snapshot)


class InvariantTest(unittest.TestCase):
    def test_limit_per_side(self):
        draft = Draft(["h1", "h2", "h3"], deadline=100, limit=1)
        ban(draft, "a", "h1", 10)
        with self.assertRaises(DraftError):
            ban(draft, "a", "h2", 20)
        self.assertEqual(draft.bans["a"], ["h1"])

    def test_replaying_same_batch_gives_same_result(self):
        def run():
            draft = Draft(["h1", "h2", "h3", "h4"], deadline=50, limit=2)
            for side, hero, now in [("a", "h1", 10), ("b", "h1", 20),
                                    ("a", "h2", 30), ("b", "ghost", 40)]:
                try:
                    ban(draft, side, hero, now)
                except DraftError:
                    pass
            return resolve(draft, 100), draft.bans

        self.assertEqual(run(), run())


class PerformanceTest(unittest.TestCase):
    def test_100k_submissions_under_one_second(self):
        pool = ["hero%03d" % i for i in range(200)]
        draft = Draft(pool, deadline=10 ** 9, limit=100)
        started = time.perf_counter()
        for i in range(100000):
            try:
                ban(draft, "ab"[i % 2], pool[i % 200], i)
            except DraftError:
                pass
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 1.0)
        self.assertEqual(resolve(draft, 100000), 200)


class ReferenceDraft:
    """参考实现：去重校验 + 超时默认。"""

    def __init__(self, pool, deadline, limit):
        self.pool = list(pool)
        self.deadline = deadline
        self.limit = limit
        self.bans = {"a": [], "b": []}

    def _banned(self):
        return set(self.bans["a"]) | set(self.bans["b"])

    def _defaults(self):
        for side in ("a", "b"):
            while len(self.bans[side]) < self.limit:
                nxt = None
                for hero in self.pool:
                    if hero not in self._banned():
                        nxt = hero
                        break
                if nxt is None:
                    break
                self.bans[side].append(nxt)

    def ban(self, side, hero, now):
        if hero not in self.pool:
            return "error"
        if self.deadline and now > self.deadline:
            self._defaults()
            return "error"
        if hero in self._banned():
            return "error"
        if len(self.bans[side]) >= self.limit:
            return "error"
        self.bans[side].append(hero)
        return "ok"

    def resolve(self, now):
        if self.deadline and now > self.deadline:
            self._defaults()
        return len(self.bans["a"]) + len(self.bans["b"])


class DifferentialTest(unittest.TestCase):
    def test_matches_reference_on_random_sequences(self):
        rng = random.Random(20260930)
        diffs = 0
        for _ in range(200):
            pool = ["hero%02d" % i for i in range(rng.randint(2, 8))]
            deadline = rng.randint(0, 30)
            limit = rng.randint(1, 3)
            draft = Draft(pool, deadline=deadline, limit=limit)
            ref = ReferenceDraft(pool, deadline, limit)
            for _ in range(rng.randint(1, 40)):
                side = rng.choice("ab")
                if rng.random() < 0.3:
                    hero = rng.choice(["ghost", ""])
                else:
                    hero = rng.choice(pool + pool[:1])
                now = rng.randint(0, 60)
                try:
                    ban(draft, side, hero, now)
                    got = "ok"
                except DraftError:
                    got = "error"
                want = ref.ban(side, hero, now)
                if got != want or draft.bans != ref.bans:
                    diffs += 1
                now_resolve = rng.randint(0, 60)
                if resolve(draft, now_resolve) != ref.resolve(now_resolve):
                    diffs += 1
                if draft.bans != ref.bans:
                    diffs += 1
        self.assertEqual(diffs, 0)


if __name__ == "__main__":
    unittest.main()
