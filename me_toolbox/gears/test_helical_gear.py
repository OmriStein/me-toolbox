"""Tests for HelicalGear, which inherits from SpurGear (not Gear directly) and
overrides pitch_diameter/ZI/Y_j/calc_forces, adding tangent/axial pitch & modulus
geometry driven by helix_angle.
"""
import unittest
from math import radians, tan, atan, degrees, cos, sin

from me_toolbox.gears import HelicalGear, SpurGear


def make_helical(**overrides):
    """Mirrors the helical gear built in examples/gears_examples/Gears_examples.py."""
    defaults = dict(
        modulus=2, pressure_angle=20, teeth_num=37, rpm=2500, grade=1,
        Qv=12, crowned=False, adjusted=False, width=50, bearing_span=100,
        pinion_offset=22.4, enclosure='precision enclosed', hardness=160,
        number_of_cycles=1e6, material='steel', helix_angle=20, sensitive_use=True,
    )
    defaults.update(overrides)
    return HelicalGear(**defaults)


class TestHelicalGear(unittest.TestCase):
    def setUp(self):
        self.helical = make_helical()
        self.gear2 = make_helical(teeth_num=92, rpm=2500 / 2.5)

    def test_is_subclass_of_spur_gear(self):
        self.assertIsInstance(self.helical, SpurGear)

    def test_repr(self):
        self.assertEqual(
            repr(self.helical),
            "HelicalGear(m=2, N=37, \N{GREEK SMALL LETTER PHI}=20, "
            "\N{GREEK SMALL LETTER PSI}=20, b=50)")

    def test_tangent_modulus(self):
        expected = self.helical.modulus / cos(radians(self.helical.helix_angle))
        self.assertAlmostEqual(self.helical.tangent_modulus, expected)
        self.assertAlmostEqual(self.helical.tangent_modulus, 2.128355544951824)

    def test_axial_modulus(self):
        expected = self.helical.modulus / sin(radians(self.helical.helix_angle))
        self.assertAlmostEqual(self.helical.axial_modulus, expected)
        self.assertAlmostEqual(self.helical.axial_modulus, 5.847608800326175)

    def test_tangent_pitch(self):
        expected = self.helical.pitch / cos(radians(self.helical.helix_angle))
        self.assertAlmostEqual(self.helical.tangent_pitch, expected)
        self.assertAlmostEqual(self.helical.tangent_pitch, 6.6864261442477515)

    def test_axial_pitch(self):
        expected = self.helical.pitch / sin(radians(self.helical.helix_angle))
        self.assertAlmostEqual(self.helical.axial_pitch, expected)
        self.assertAlmostEqual(self.helical.axial_pitch, 18.370804848171733)

    def test_tangent_pressure_angle(self):
        expected = degrees(atan(
            tan(radians(self.helical.pressure_angle)) / cos(radians(self.helical.helix_angle))))
        self.assertAlmostEqual(self.helical.tangent_pressure_angle, expected)
        self.assertAlmostEqual(self.helical.tangent_pressure_angle, 21.17283218516298)

    def test_pitch_diameter_overridden_with_tangent_modulus(self):
        # HelicalGear.pitch_diameter uses tangent_modulus, unlike the base Gear/SpurGear
        # formula which just uses modulus
        expected = self.helical.teeth_num * self.helical.tangent_modulus
        self.assertAlmostEqual(self.helical.pitch_diameter, expected)
        self.assertAlmostEqual(self.helical.pitch_diameter, 78.7491551632175)

    def test_calc_centers_distance_uses_tangent_modulus(self):
        gear_ratio = 2.5
        expected = 0.5 * self.helical.tangent_modulus * self.helical.teeth_num * (gear_ratio + 1)
        self.assertAlmostEqual(self.helical.calc_centers_distance(gear_ratio), expected)
        self.assertAlmostEqual(self.helical.calc_centers_distance(gear_ratio), 137.81102153563063)

    def test_calc_forces_returns_axial_component(self):
        Wt, Wr, Wx = HelicalGear.calc_forces(self.helical, 50e3)
        self.assertAlmostEqual(Wt, 4850.488397353143)
        self.assertAlmostEqual(Wr, 31.284209279785653)
        self.assertAlmostEqual(Wx, 1765.4333982901198)
        self.assertAlmostEqual(Wx, Wt * tan(radians(self.helical.helix_angle)))

    def test_ZI(self):
        self.assertAlmostEqual(HelicalGear.ZI(self.helical, self.gear2), 0.194416669862086)

    def test_ZI_raises_when_width_too_small(self):
        narrow = make_helical(width=1)
        narrow2 = make_helical(width=1, teeth_num=92)
        with self.assertRaises(ValueError):
            HelicalGear.ZI(narrow, narrow2)

    def test_Y_j_sets_same_Yj_on_both_gears(self):
        HelicalGear.Y_j(self.helical, self.gear2)
        self.assertAlmostEqual(self.helical.Yj, 0.5673721386666668)
        self.assertAlmostEqual(self.gear2.Yj, 0.5673721386666668)
        self.assertEqual(self.helical.Yj, self.gear2.Yj)

    def test_check_compatibility_matching_gears_ok(self):
        self.helical.check_compatibility(self.gear2)  # should not raise

    def test_check_compatibility_mismatched_helix_angle_raises(self):
        other = make_helical(helix_angle=25, teeth_num=92)
        with self.assertRaises(ValueError):
            self.helical.check_compatibility(other)

    def test_check_compatibility_mismatched_pressure_angle_raises(self):
        other = make_helical(pressure_angle=25, teeth_num=92, helix_angle=20)
        with self.assertRaises(ValueError):
            self.helical.check_compatibility(other)

    def test_create_new_gear(self):
        new_gear = HelicalGear.create_new_gear(
            HelicalGear.format_properties(self.helical.__dict__))
        self.assertIsInstance(new_gear, HelicalGear)
        self.assertEqual(new_gear.teeth_num, self.helical.teeth_num)
        self.assertEqual(new_gear.helix_angle, self.helical.helix_angle)

    def test_format_properties_keeps_helix_angle(self):
        formatted = HelicalGear.format_properties(self.helical.__dict__)
        self.assertIn('helix_angle', formatted)
        self.assertEqual(formatted['helix_angle'], 20)


if __name__ == '__main__':
    unittest.main()
