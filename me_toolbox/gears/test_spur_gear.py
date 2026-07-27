"""Tests for the SpurGear class (adds AGMA spur-specific geometry factors on top
of Gear: ZI, Yj table lookups via Y_j, calc_forces, calc_centers_distance,
check_compatibility, create_new_gear/format_properties).
"""
import unittest
from math import pi, tan, radians, cos, sin

from me_toolbox.gears import SpurGear, HelicalGear


def make_pinion(**overrides):
    """Mirrors the pinion built in examples/gears_examples/Gears_examples.py."""
    defaults = dict(
        modulus=4, pressure_angle=25, teeth_num=25, rpm=1500, grade=2,
        Qv=11, crowned=False, adjusted=True, width=25, bearing_span=10,
        pinion_offset=2, enclosure='extra precision enclosed', hardness=400,
        number_of_cycles=1e8, material='steel', sensitive_use=True,
    )
    defaults.update(overrides)
    return SpurGear(**defaults)


class TestSpurGear(unittest.TestCase):
    def setUp(self):
        self.pinion = make_pinion()
        self.gear2 = make_pinion(teeth_num=78, rpm=1500 / 3.1)

    def test_repr(self):
        self.assertEqual(repr(self.pinion), "SpurGear(m=4, N=25, \N{GREEK SMALL LETTER PHI}=25, b=25)")

    def test_ZI(self):
        mG = self.gear2.teeth_num / self.pinion.teeth_num
        phi = radians(self.pinion.pressure_angle)
        expected = 0.5 * cos(phi) * sin(phi) * (mG / (mG + 1))
        self.assertAlmostEqual(SpurGear.ZI(self.pinion, self.gear2), expected)
        self.assertAlmostEqual(SpurGear.ZI(self.pinion, self.gear2), 0.14502783146427253)

    def test_calc_centers_distance(self):
        gear_ratio = 3.1
        expected = 0.5 * self.pinion.modulus * self.pinion.teeth_num * (gear_ratio + 1)
        self.assertAlmostEqual(self.pinion.calc_centers_distance(gear_ratio), expected)
        self.assertAlmostEqual(self.pinion.calc_centers_distance(gear_ratio), 204.99999999999997)

    def test_calc_forces(self):
        Wt, Wr = SpurGear.calc_forces(self.pinion, 50e3)
        self.assertAlmostEqual(Wt, 6366.197723675814)
        self.assertAlmostEqual(Wr, Wt * tan(radians(self.pinion.pressure_angle)))

    def test_Y_j_sets_Yj_on_both_gears(self):
        SpurGear.Y_j(self.pinion, self.gear2)
        self.assertAlmostEqual(self.pinion.Yj, 0.469905)
        self.assertAlmostEqual(self.gear2.Yj, 0.5339848)

    def test_get_factors_reports_none_before_transmission(self):
        # YN/ZN/Yj/Zw all depend on state a Transmission normally populates
        factors = self.pinion.get_factors(verbose=False)
        self.assertIsNone(factors['YN'])
        self.assertIsNone(factors['ZN'])
        self.assertIsNone(factors['Yj'])
        self.assertIsNone(factors['Zw'])

    def test_check_compatibility_matching_gears_ok(self):
        # should not raise
        self.pinion.check_compatibility(self.gear2)

    def test_check_compatibility_mismatched_pressure_angle_raises(self):
        other = make_pinion(pressure_angle=20, teeth_num=78)
        with self.assertRaises(ValueError):
            self.pinion.check_compatibility(other)

    def test_check_compatibility_mismatched_modulus_raises(self):
        other = make_pinion(modulus=2, teeth_num=78)
        with self.assertRaises(ValueError):
            self.pinion.check_compatibility(other)

    def test_check_compatibility_mismatched_type_raises(self):
        helical = HelicalGear(modulus=4, pressure_angle=25, teeth_num=78, rpm=500, grade=2,
                              Qv=11, width=25, bearing_span=10, pinion_offset=2,
                              enclosure='extra precision enclosed', hardness=400,
                              number_of_cycles=1e8, helix_angle=20)
        with self.assertRaises(ValueError):
            self.pinion.check_compatibility(helical)

    def test_create_new_gear(self):
        new_gear = SpurGear.create_new_gear(SpurGear.format_properties(self.pinion.__dict__))
        self.assertIsInstance(new_gear, SpurGear)
        self.assertEqual(new_gear.teeth_num, self.pinion.teeth_num)
        self.assertEqual(new_gear.modulus, self.pinion.modulus)

    def test_format_properties_strips_extra_keys(self):
        raw = dict(self.pinion.__dict__)
        raw['contact_ratio'] = 1.5  # not a constructor kwarg, should be dropped
        raw['Zw'] = None
        formatted = SpurGear.format_properties(raw)
        self.assertNotIn('contact_ratio', formatted)
        self.assertNotIn('Zw', formatted)
        self.assertIn('modulus', formatted)
        self.assertIn('teeth_num', formatted)


if __name__ == '__main__':
    unittest.main()
