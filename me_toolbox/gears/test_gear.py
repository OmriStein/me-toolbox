"""Tests for the Gear base class.

Gear is a plain class (not abstract), so it's tested by instantiating it directly
with realistic values in the same style as the worked example in
examples/gears_examples/Gears_examples.py.

Note: YN/ZN/cycles_or_hours() are driven by `self.contact_ratio`, which is only
ever populated by Transmission._contact_ratio() in normal usage. To exercise those
properties on a bare Gear (without building a whole Transmission), the tests below
set `contact_ratio` manually before calling them - this mirrors exactly what
Transmission does internally.
"""
import unittest
from math import pi, tan, radians

from me_toolbox.gears import Gear


def make_gear(**overrides):
    """Build a Gear with realistic defaults (mirrors the pinion in the worked example),
    overriding whichever kwargs are passed in.
    """
    defaults = dict(
        modulus=4, teeth_num=25, rpm=1500, Qv=11, width=25, bearing_span=10,
        pinion_offset=2, enclosure='extra precision enclosed', hardness=400,
        pressure_angle=25, grade=2, work_hours=0, number_of_cycles=1e8,
        crowned=False, adjusted=True, sensitive_use=True, nitriding=False,
        case_carb=False, material='steel',
    )
    defaults.update(overrides)
    return Gear(**defaults)


class TestGear(unittest.TestCase):
    def setUp(self):
        self.gear = make_gear()
        # a compatible mate for Y_j (same pressure angle, different teeth number)
        self.gear2 = make_gear(teeth_num=78, rpm=1500 / 3.1)

    def test_constructor_requires_cycles_or_hours(self):
        with self.assertRaises(ValueError):
            make_gear(work_hours=0, number_of_cycles=0)

    def test_pitch_diameter(self):
        self.assertAlmostEqual(self.gear.pitch_diameter,
                               self.gear.teeth_num * self.gear.modulus)

    def test_pitch(self):
        self.assertAlmostEqual(self.gear.pitch, self.gear.modulus * pi)

    def test_tangent_velocity(self):
        self.assertAlmostEqual(
            self.gear.tangent_velocity,
            (pi * self.gear.pitch_diameter * self.gear.rpm) / 60e3)

    def test_ZR_is_always_one(self):
        self.assertEqual(self.gear.ZR, 1)

    # --- KB (rim thickness factor) ---
    def test_KB_large_teeth_num_is_one(self):
        # teeth_num=25 -> mB = (0.5*25-1.25)/2.25 = 5 >= 1.2
        self.assertAlmostEqual(self.gear.KB, 1)

    def test_KB_small_teeth_num(self):
        small = make_gear(teeth_num=6)  # mB = (0.5*6-1.25)/2.25 = 0.7778 < 1.2
        self.assertAlmostEqual(small.KB, 1.6938924046893988)

    # --- Kv (dynamic factor) ---
    def test_Kv_mid_range_qv(self):
        self.assertAlmostEqual(self.gear.Kv, 1.093690558843225)
        self.assertAlmostEqual(self.gear.maximum_velocity, 50.0)

    def test_Kv_qv5(self):
        gear = make_gear(Qv=5)
        self.assertAlmostEqual(gear.Kv, 1.7926654595212022)

    def test_Kv_qv12_has_no_maximum_velocity(self):
        gear = make_gear(Qv=12)
        self.assertAlmostEqual(gear.Kv, 1)
        self.assertEqual(gear.maximum_velocity, "Qv=12 no maximum velocity")

    def test_Kv_invalid_qv_raises(self):
        gear = make_gear(Qv=13)
        with self.assertRaises(ValueError):
            gear.Kv

    # --- Ks (size factor) ---
    def test_Ks_large_pitch(self):
        # modulus=4 -> pitch = 4*pi = 12.566 > 8
        self.assertAlmostEqual(self.gear.Ks, 1.07508178122845)

    def test_Ks_small_pitch_is_one(self):
        gear = make_gear(modulus=2)  # pitch = 2*pi = 6.283 <= 8
        self.assertAlmostEqual(gear.Ks, 1)

    # --- KH (load distribution factor) ---
    def test_KH_default(self):
        self.assertAlmostEqual(self.gear.KH, 1.0658765)

    def test_KH_crowned(self):
        gear = make_gear(crowned=True)
        self.assertAlmostEqual(gear.KH, 1.0527012)

    def test_KH_low_pinion_offset_ratio(self):
        # s1/s = 2/100 = 0.02 < 0.175 -> K_Hpm = 1
        gear = make_gear(bearing_span=100, pinion_offset=2)
        self.assertAlmostEqual(gear.KH, 1.0633765)

    def test_KH_high_pinion_offset_ratio(self):
        # s1/s = 20/100 = 0.2 >= 0.175 -> K_Hpm = 1.1
        gear = make_gear(bearing_span=100, pinion_offset=20)
        self.assertAlmostEqual(gear.KH, 1.0658765)

    def test_KH_width_mid_range(self):
        gear = make_gear(width=100)
        self.assertAlmostEqual(gear.KH, 1.184414)

    def test_KH_width_high_range(self):
        gear = make_gear(width=500)
        self.assertAlmostEqual(gear.KH, 5.979234999999999)

    def test_KH_width_out_of_range_raises(self):
        gear = make_gear(width=1100)
        with self.assertRaises(ValueError):
            gear.KH

    def test_KH_enclosure_types(self):
        expected = {
            'open gearing': 1.2381807,
            'commercial enclosed': 1.1414555,
            'precision enclosed': 1.091508,
            'extra precision enclosed': 1.0658765,
        }
        for enclosure, value in expected.items():
            with self.subTest(enclosure=enclosure):
                gear = make_gear(enclosure=enclosure)
                self.assertAlmostEqual(gear.KH, value)

    # --- St / Sc (bending / contact safety factor) ---
    def test_St_grade2(self):
        self.assertAlmostEqual(self.gear.St, 0.703 * self.gear.hardness + 113)

    def test_St_grade1(self):
        gear = make_gear(grade=1)
        self.assertAlmostEqual(gear.St, 0.533 * gear.hardness + 88.3)

    def test_St_invalid_grade_raises(self):
        gear = make_gear(grade=3)
        with self.assertRaises(ValueError):
            gear.St

    def test_Sc_grade2(self):
        self.assertAlmostEqual(self.gear.Sc, 237 + 2.41 * self.gear.hardness)

    def test_Sc_grade1(self):
        gear = make_gear(grade=1)
        self.assertAlmostEqual(gear.Sc, 200 + 2.22 * gear.hardness)

    def test_Sc_invalid_grade_raises(self):
        gear = make_gear(grade=3)
        with self.assertRaises(ValueError):
            gear.Sc

    # --- cycles_or_hours / YN / ZN ---
    def test_cycles_or_hours_none_before_contact_ratio_set(self):
        # contact_ratio is None until a Transmission computes it
        self.assertIsNone(self.gear.cycles_or_hours())
        self.assertIsNone(self.gear.YN)
        self.assertIsNone(self.gear.ZN)

    def test_cycles_or_hours_from_work_hours(self):
        gear = make_gear(work_hours=1000, number_of_cycles=0)
        gear.contact_ratio = 1.5
        self.assertAlmostEqual(gear.cycles_or_hours(), 60 * 1000 * gear.rpm * 1.5)

    def test_cycles_or_hours_from_number_of_cycles(self):
        gear = make_gear(work_hours=0, number_of_cycles=1e8)
        gear.contact_ratio = 1.5
        self.assertAlmostEqual(gear.cycles_or_hours(), 1e8)

    def test_cycles_or_hours_matching_both_inputs(self):
        rpm, contact_ratio, hours = 1500, 1.5, 1000
        cycles = 60 * hours * rpm * contact_ratio
        gear = make_gear(rpm=rpm, work_hours=hours, number_of_cycles=cycles)
        gear.contact_ratio = contact_ratio
        self.assertAlmostEqual(gear.cycles_or_hours(), cycles)

    def test_cycles_or_hours_mismatching_both_inputs_raises(self):
        gear = make_gear(work_hours=1000, number_of_cycles=123)
        gear.contact_ratio = 1.5
        with self.assertRaises(ValueError):
            gear.cycles_or_hours()

    def test_YN_low_cycle_by_hardness(self):
        expected = {160: 1.248462933568279, 250: 1.4834131106023007, 400: 1.7199448575409844}
        for hardness, value in expected.items():
            with self.subTest(hardness=hardness):
                gear = make_gear(hardness=hardness, number_of_cycles=1e5)
                gear.contact_ratio = 1.5
                self.assertAlmostEqual(gear.YN, value)

    def test_YN_low_cycle_nitrided(self):
        gear = make_gear(number_of_cycles=1e5, nitriding=True)
        gear.contact_ratio = 1.5
        self.assertAlmostEqual(gear.YN, 1.3730057888794405)

    def test_YN_low_cycle_case_carb(self):
        gear = make_gear(number_of_cycles=1e5, case_carb=True)
        gear.contact_ratio = 1.5
        self.assertAlmostEqual(gear.YN, 1.559459025764483)

    def test_YN_high_cycle_sensitive_use(self):
        gear = make_gear(number_of_cycles=1e7, sensitive_use=True)
        gear.contact_ratio = 1.5
        self.assertAlmostEqual(gear.YN, 1.0000228418849015)

    def test_YN_high_cycle_not_sensitive_use(self):
        gear = make_gear(number_of_cycles=1e7, sensitive_use=False)
        gear.contact_ratio = 1.5
        self.assertAlmostEqual(gear.YN, 1.0176434217392432)

    def test_ZN_low_cycle_nitrided(self):
        gear = make_gear(number_of_cycles=1e6, nitriding=True)
        gear.contact_ratio = 1.5
        self.assertAlmostEqual(gear.ZN, 1.0321966337030288)

    def test_ZN_low_cycle_not_nitrided(self):
        gear = make_gear(number_of_cycles=1e6, nitriding=False)
        gear.contact_ratio = 1.5
        self.assertAlmostEqual(gear.ZN, 1.1376091388658955)

    def test_ZN_high_cycle_sensitive_use(self):
        gear = make_gear(number_of_cycles=5e6, sensitive_use=True)
        gear.contact_ratio = 1.5
        self.assertAlmostEqual(gear.ZN, 1.0395628522362972)

    def test_ZN_high_cycle_not_sensitive_use(self):
        gear = make_gear(number_of_cycles=5e6, sensitive_use=False)
        gear.contact_ratio = 1.5
        self.assertAlmostEqual(gear.ZN, 1.0160898830050287)

    # --- Y_j (static, mutates both gears) ---
    def test_Y_j_pressure_angle_25(self):
        Gear.Y_j(self.gear, self.gear2)
        self.assertAlmostEqual(self.gear.Yj, 0.469905)
        self.assertAlmostEqual(self.gear2.Yj, 0.5339848)

    def test_Y_j_pressure_angle_20(self):
        gear1 = make_gear(pressure_angle=20, teeth_num=25)
        gear2 = make_gear(pressure_angle=20, teeth_num=78)
        Gear.Y_j(gear1, gear2)
        self.assertAlmostEqual(gear1.Yj, 0.391701)
        self.assertAlmostEqual(gear2.Yj, 0.44285040000000003)

    def test_Y_j_invalid_pressure_angle_raises(self):
        gear1 = make_gear(pressure_angle=30, teeth_num=25)
        gear2 = make_gear(pressure_angle=30, teeth_num=78)
        with self.assertRaises(ValueError):
            Gear.Y_j(gear1, gear2)

    # --- calc_forces (static) ---
    def test_calc_forces(self):
        Wt, Wr = Gear.calc_forces(self.gear, 50e3)
        expected_Wt = (60e3 / pi) * (50e3 / (self.gear.pitch_diameter * self.gear.rpm))
        self.assertAlmostEqual(Wt, expected_Wt)
        self.assertAlmostEqual(Wr, Wt * tan(radians(self.gear.pressure_angle)))


if __name__ == '__main__':
    unittest.main()
