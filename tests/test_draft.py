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
