import unittest
from math import sqrt

from me_toolbox.fatigue import FailureCriteria


class TestFailureCriteria(unittest.TestCase):

    def setUp(self):
        self.Sut = 700
        self.Sy = 525
        self.Se = 200
        self.alt = 100
        self.mean = 50

    def test_modified_goodman(self):
        result = FailureCriteria.modified_goodman(self.Sut, self.Se, self.alt, self.mean)
        expected = 1 / ((self.alt / self.Se) + (self.mean / self.Sut))
        self.assertAlmostEqual(result, expected)
        self.assertAlmostEqual(result, 1.75)

    def test_modified_goodman_negative_mean_raises(self):
        self.assertRaises(ValueError, FailureCriteria.modified_goodman,
                          self.Sut, self.Se, self.alt, -10)

    def test_soderberg(self):
        result = FailureCriteria.soderberg(self.Sy, self.Se, self.alt, self.mean)
        expected = 1 / ((self.alt / self.Se) + (self.mean / self.Sy))
        self.assertAlmostEqual(result, expected)
        self.assertAlmostEqual(result, 1.68)

    def test_soderberg_negative_mean_raises(self):
        self.assertRaises(ValueError, FailureCriteria.soderberg,
                          self.Sy, self.Se, self.alt, -10)

    def test_gerber(self):
        result = FailureCriteria.gerber(self.Sut, self.Se, self.alt, self.mean)
        alpha = self.Sut / self.mean
        beta = self.alt / self.Se
        expected = 0.5 * alpha ** 2 * beta * (-1 + sqrt(1 + 4 * alpha ** -2 * beta ** -2))
        # gerber uses sympy.sqrt internally so the result is a sympy Float,
        # wrap in float() before comparing (see test_helical_compression_spring.py)
        self.assertAlmostEqual(float(result), expected)
        self.assertAlmostEqual(float(result), 1.9607692249636295)

    def test_gerber_negative_mean_raises(self):
        self.assertRaises(ValueError, FailureCriteria.gerber,
                          self.Sut, self.Se, self.alt, -10)

    def test_asme_elliptic(self):
        result = FailureCriteria.asme_elliptic(self.Sy, self.Se, self.alt, self.mean)
        expected = sqrt(1 / ((self.alt / self.Se) ** 2 + (self.mean / self.Sy) ** 2))
        self.assertAlmostEqual(float(result), expected)
        self.assertAlmostEqual(float(result), 1.9646771328449495)

    def test_asme_elliptic_negative_mean_raises(self):
        self.assertRaises(ValueError, FailureCriteria.asme_elliptic,
                          self.Sy, self.Se, self.alt, -10)

    def test_langer_static_yield_first_quadrant(self):
        # mean_eq_stress > 0 -> Sy / (alt + mean)
        result = FailureCriteria.langer_static_yield(self.Sy, self.alt, self.mean)
        self.assertAlmostEqual(result, self.Sy / (self.alt + self.mean))
        self.assertAlmostEqual(result, 3.5)

    def test_langer_static_yield_second_quadrant(self):
        # mean_eq_stress <= 0 -> Sy / (alt - mean)
        result = FailureCriteria.langer_static_yield(self.Sy, self.alt, -self.mean)
        self.assertAlmostEqual(result, self.Sy / (self.alt - (-self.mean)))
        self.assertAlmostEqual(result, 3.5)

    def test_get_safety_factors_modified_goodman(self):
        fatigue_sf, static_sf = FailureCriteria.get_safety_factors(
            self.Sy, self.Sut, self.Se, self.alt, self.mean, 'modified goodman')
        self.assertAlmostEqual(fatigue_sf, 1.75)
        self.assertAlmostEqual(static_sf, 3.5)

    def test_get_safety_factors_soderberg(self):
        fatigue_sf, static_sf = FailureCriteria.get_safety_factors(
            self.Sy, self.Sut, self.Se, self.alt, self.mean, 'soderberg')
        self.assertAlmostEqual(fatigue_sf, 1.68)
        self.assertAlmostEqual(static_sf, 3.5)

    def test_get_safety_factors_gerber(self):
        fatigue_sf, static_sf = FailureCriteria.get_safety_factors(
            self.Sy, self.Sut, self.Se, self.alt, self.mean, 'gerber')
        self.assertAlmostEqual(float(fatigue_sf), 1.96076922496363)
        self.assertAlmostEqual(static_sf, 3.5)

    def test_get_safety_factors_asme_elliptic(self):
        fatigue_sf, static_sf = FailureCriteria.get_safety_factors(
            self.Sy, self.Sut, self.Se, self.alt, self.mean, 'asme-elliptic')
        self.assertAlmostEqual(float(fatigue_sf), 1.96467713284495)
        self.assertAlmostEqual(static_sf, 3.5)

    def test_get_safety_factors_unknown_criterion_raises(self):
        self.assertRaises(Exception, FailureCriteria.get_safety_factors,
                          self.Sy, self.Sut, self.Se, self.alt, self.mean, 'bogus')

    def test_get_safety_factors_negative_mean_uses_fatigue_alternative(self):
        # when mean_eq_stress <= 0 the dynamic safety factor is Se/alt regardless
        # of the requested criterion, and static is still Langer
        fatigue_sf, static_sf = FailureCriteria.get_safety_factors(
            self.Sy, self.Sut, self.Se, self.alt, -10, 'modified goodman')
        self.assertAlmostEqual(fatigue_sf, self.Se / self.alt)
        self.assertAlmostEqual(fatigue_sf, 2.0)
        self.assertAlmostEqual(static_sf, 4.7727272727272725)


if __name__ == '__main__':
    unittest.main()
