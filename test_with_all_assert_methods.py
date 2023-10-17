"""Dummy test for use in certain tests in test_py_holmes.py
"""


import unittest


class TestWithAllAssertMethods(unittest.TestCase):
    def test_with_all_assert_methods(self):
        self.assertEqual(1, 2)

        self.assertNotEqual(1, 1)

        self.assertTrue(False)

        self.assertFalse(True)

        self.assertIs("hi", "bye")

        self.assertIsNot("hi", "hi")

        self.assertIsNone("hi")

        self.assertIsNotNone(None)

        self.assertIn("beans", ["eggs", "fish"])

        self.assertIn("beans", ["eggs", "fish"])    # Intentional duplicate

        self.assertNotIn("beans", ["beans", "eggs", "fish"])

        self.assertNotIn("beans", ["beans", "eggs", "fish"])    # Intentional duplicate

        self.assertIsInstance("hi", int)

        self.assertNotIsInstance("hi", str)

        with self.assertRaises(ValueError):
            my_var = 2 + 2

        with self.assertRaisesRegexp(ValueError, "foo"):
            raise ValueError("bar")

        self.assertAlmostEqual(3, 4)

        self.assertNotAlmostEqual(3, 3.0000000000000000000000000000000000000000000000001)

        self.assertGreater(0, 1)

        self.assertGreaterEqual(0, 1)

        self.assertLess(1, 0)

        self.assertLessEqual(1, 0)

        self.assertRegexpMatches("bot", "bat")

        self.assertRegexpMatches("bot", "bat")  # Intentional duplicate

        self.assertNotRegexpMatches("bot", "bot")

        self.assertNotRegexpMatches("bot", "bot")   # Intentional duplicate

        self.assertCountEqual(["foo", "bar"], ["foo", "bees"])

        with self.assertWarns(UserWarning):
            my_var = 2 + 2

        with self.assertWarnsRegex(RuntimeWarning, "oh no"):
            my_var = 2 + 2

        with self.assertLogs("foo", level="INFO") as cm:
            my_var = 2 + 2

        a = """this
        is
        a
        string"""
        b = """here's
        a
        different
        string"""
        self.assertMultiLineEqual(a, b)

        self.assertSequenceEqual([0, 5, 10], [0, 10, 20])

        self.assertListEqual([0, 5, 10], [0, 10, 20])

        self.assertTupleEqual((0, 5, 10), (0, 10, 20))

        self.assertSetEqual({0, 5, 10}, {0, 10, 20})

        self.assertDictEqual({"foo": "bar"}, {"fuzz": "buzz"})
