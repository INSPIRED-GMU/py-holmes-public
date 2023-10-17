"""Unit test methods to be used in test_py_holmes.TestUnitTestFinding.test_cut_found_tests()"""


import unittest
from circle_method import circle_area
from math import pi


class TestCircleArea(unittest.TestCase):
    def test_original(self):
        """Original test on which the variants below are based."""
        self.assertAlmostEqual(pi, circle_area(1))
        self.assertNotAlmostEqual(100, circle_area(0))
        self.assertGreater(100 * pi * 2.1 ** 2, circle_area(2.1))

    def test_variant_0(self):
        """Should count as call-similar.
        Exactly the same as test_original
        """
        self.assertAlmostEqual(pi, circle_area(1))
        self.assertNotAlmostEqual(100, circle_area(0))
        self.assertGreater(100 * pi * 2.1 ** 2, circle_area(2.1))

    def test_variant_1(self):
        """Should count as call-similar.
        Methods are called with different arguments.
        """
        self.assertAlmostEqual(pi * 10, circle_area(1) * 100)
        self.assertNotAlmostEqual(200, circle_area(0))
        self.assertGreater(200 * pi * 2.1 ** 2, circle_area(2.1))

    def test_variant_2(self):
        """Should NOT count as call-similar.
        Methods are called in a different order.
        """
        self.assertNotAlmostEqual(100, circle_area(0))
        self.assertAlmostEqual(pi, circle_area(1))
        self.assertGreater(100 * pi * 2.1 ** 2, circle_area(2.1))

    def test_variant_3(self):
        """Should NOT count as call-similar.
        One fewer call takes place.
        """
        self.assertAlmostEqual(pi, circle_area(1))
        self.assertNotAlmostEqual(100, circle_area(0))

    def test_variant_4(self):
        """Should NOT count as call-similar.
        One more call takes place.
        """
        self.assertAlmostEqual(pi, circle_area(1))
        self.assertNotAlmostEqual(100, circle_area(0))
        self.assertGreater(100 * pi * 2.1 ** 2, circle_area(2.1))
        self.assertLess(-100, circle_area(1))

    def test_variant_5(self):
        """Should NOT count as call-similar.
        One of the method calls is replaced with a different method call.
        """
        self.assertLess(-100, circle_area(1))
        self.assertNotAlmostEqual(100, circle_area(0))
        self.assertGreater(100 * pi * 2.1 ** 2, circle_area(2.1))

    def test_variant_6(self):
        """Should count as call-similar.
        Calls a method in a different way
        """
        self.assertAlmostEqual(pi, circle_area(1))
        self.assertNotAlmostEqual(100, circle_area(0))
        unittest.TestCase.assertGreater(self, 100 * pi * 2.1 ** 2, circle_area(2.1))
