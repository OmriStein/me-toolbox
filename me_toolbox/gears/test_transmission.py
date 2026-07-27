"""Tests for Transmission, which wires two gears together and computes AGMA
strength-check factors/stresses on top of them.
"""
import unittest
from math import log

from me_toolbox.gears import SpurGear, HelicalGear, Transmission
from me_toolbox.gears.transmission import GearTypeError


def make_pinion(**overrides):
    defaults = dict(
        modulus=4, pressure_angle=25, teeth_num=25, rpm=1500, grade=2,
        Qv=11, crowned=False, adjusted=True, width=25, bearing_span=10,
        pinion_offset=2, enclosure='extra precision enclosed', hardness=400,
        number_of_cycles=1e8, material='steel', sensitive_use=True,
    )
    defaults.update(overrides)
    return SpurGear(**defaults)


def make_helical(**overrides):
    defaults = dict(
        modulus=2, pressure_angle=20, teeth_num=37, rpm=2500, grade=1,
        Qv=12, crowned=False, adjusted=False, width=50, bearing_span=100,
        pinion_offset=22.4, enclosure='precision enclosed', hardness=160,
        number_of_cycles=1e6, material='steel', helix_angle=20, sensitive_use=True,
    )
    defaults.update(overrides)
    return HelicalGear(**defaults)


class TestTransmissionSpurGears(unittest.TestCase):
    """Uses gear_ratio (no explicit gear2) - Transmission builds gear2 itself,
    exactly like the worked example.
    """

    def setUp(self):
        self.pinion = make_pinion()
        self.gearbox = Transmission(
            gear1=self.pinion, oil_temp=65, reliability=0.999, power=50e3,
            gear_ratio=3.1, driving_machine='light shock', driven_machine='moderate shock',
            SF=1.1, SH=1)

    def test_gear2_is_generated_from_gear_ratio(self):
        self.assertEqual(self.gearbox.gear2.teeth_num, 78)  # round(25*3.1)
        self.assertAlmostEqual(self.gearbox.gear2.rpm, 1500 / 3.1)
        self.assertIsInstance(self.gearbox.gear2, SpurGear)

    def test_contact_ratio_assigned_to_both_gears(self):
        self.assertAlmostEqual(self.gearbox.gear1.contact_ratio, 1.5113641827119686)
        self.assertEqual(self.gearbox.gear1.contact_ratio, self.gearbox.gear2.contact_ratio)

    def test_Zw_assigned_pinion_is_one(self):
        self.assertEqual(self.gearbox.gear1.Zw, 1)
        self.assertAlmostEqual(self.gearbox.gear2.Zw, 1.0)

    def test_Yj_assigned_by_constructor(self):
        self.assertAlmostEqual(self.gearbox.gear1.Yj, 0.469905)
        self.assertAlmostEqual(self.gearbox.gear2.Yj, 0.5339848)

    def test_ZI_assigned_by_constructor(self):
        self.assertAlmostEqual(self.gearbox.ZI, 0.14502783146427253)

    def test_Ko(self):
        self.assertAlmostEqual(self.gearbox.Ko, 1.5)

    def test_Ko_invalid_driving_machine_raises(self):
        gb = Transmission(gear1=self.pinion, oil_temp=65, reliability=0.999, power=50e3,
                          gear_ratio=3.1, driving_machine='bad', driven_machine='uniform',
                          SF=1.1, SH=1)
        with self.assertRaises(ValueError):
            gb.Ko

    def test_Ko_invalid_driven_machine_raises(self):
        gb = Transmission(gear1=self.pinion, oil_temp=65, reliability=0.999, power=50e3,
                          gear_ratio=3.1, driving_machine='uniform', driven_machine='bad',
                          SF=1.1, SH=1)
        with self.assertRaises(ValueError):
            gb.Ko

    def test_Ytheta_below_threshold_is_one(self):
        # oil_temp=65 <= 71
        self.assertEqual(self.gearbox.Ytheta, 1)

    def test_Ytheta_above_threshold(self):
        gb = Transmission(gear1=self.pinion, oil_temp=100, reliability=0.999, power=50e3,
                          gear_ratio=3.1, driving_machine='uniform', driven_machine='uniform',
                          SF=1, SH=1)
        self.assertAlmostEqual(gb.Ytheta, (273 + 100) / 344)

    def test_Yz_high_reliability_range(self):
        # reliability=0.999 falls in the 0.99<R<=0.9999 branch
        R = self.gearbox.reliability
        self.assertAlmostEqual(self.gearbox.Yz, 0.5 - 0.109 * log(1 - R))
        self.assertAlmostEqual(self.gearbox.Yz, 1.2529453254090528)

    def test_Yz_mid_reliability_range(self):
        # 0.9<=R<=0.99 branch
        gb = Transmission(gear1=self.pinion, oil_temp=65, reliability=0.95, power=50e3,
                          gear_ratio=3.1, driving_machine='uniform', driven_machine='uniform',
                          SF=1, SH=1)
        self.assertAlmostEqual(gb.Yz, 0.658 - 0.0759 * log(1 - 0.95))

    def test_Yz_out_of_range_raises(self):
        gb = Transmission(gear1=self.pinion, oil_temp=65, reliability=0.5, power=50e3,
                          gear_ratio=3.1, driving_machine='uniform', driven_machine='uniform',
                          SF=1, SH=1)
        with self.assertRaises(ValueError):
            gb.Yz

    def test_ZE_steel_on_steel(self):
        self.assertAlmostEqual(self.gearbox.ZE, 189.234939151512)

    def test_ZE_returns_none_for_invalid_material(self):
        # documents current (non-crashing) behavior: an unrecognized material name
        # causes a TypeError inside the sqrt, which ZE swallows and returns None from
        pinion = make_pinion(material='unobtainium')
        gb = Transmission(gear1=pinion, oil_temp=65, reliability=0.999, power=50e3,
                          gear_ratio=3.1, driving_machine='uniform', driven_machine='uniform',
                          SF=1, SH=1)
        self.assertIsNone(gb.ZE)

    def test_centers_distance(self):
        self.assertAlmostEqual(self.gearbox.centers_distance,
                               self.pinion.calc_centers_distance(self.gearbox.gear_ratio))
        self.assertAlmostEqual(self.gearbox.centers_distance, 204.99999999999997)

    def test_bending_stress(self):
        self.assertAlmostEqual(self.gearbox.bending_stress(self.gearbox.gear1), 254.6854697343694)

    def test_allowed_bending_stress(self):
        self.assertAlmostEqual(
            self.gearbox.allowed_bending_stress(self.gearbox.gear1), 265.5227483081584)

    def test_minimum_width_for_bending(self):
        self.assertAlmostEqual(
            self.gearbox.minimum_width_for_bending(self.gearbox.gear1), 23.979628050436233)

    def test_contact_stress(self):
        self.assertAlmostEqual(self.gearbox.contact_stress(self.gearbox.gear1), 1087.208304892827)

    def test_allowed_contact_stress(self):
        self.assertAlmostEqual(
            self.gearbox.allowed_contact_stress(self.gearbox.gear1), 842.5660570506676)

    def test_minimum_width_for_contact(self):
        self.assertAlmostEqual(
            self.gearbox.minimum_width_for_contact(self.gearbox.gear1), 41.625322572862196)

    def test_life_expectency_in_cycles(self):
        self.assertAlmostEqual(
            self.gearbox.life_expectency(self.gearbox.gear1), 1054525.5642632532)

    def test_life_expectency_in_hours(self):
        self.assertAlmostEqual(
            self.gearbox.life_expectency(self.gearbox.gear1, in_hours=True), 11.72)

    def test_minimal_hardness(self):
        self.assertAlmostEqual(
            self.gearbox.minimal_hardness(self.gearbox.gear1), 377.11347809285706)

    def test_get_factors(self):
        factors = self.gearbox.get_factors(verbose=False)
        self.assertAlmostEqual(factors['Ko='], 1.5)
        self.assertAlmostEqual(factors['ZI='], 0.14502783146427253)

    def test_check_undercut_runs_without_error(self):
        # just verifies it executes to completion for a normal gear ratio/pressure angle
        self.gearbox.check_undercut()


class TestTransmissionExplicitGear2(unittest.TestCase):
    def setUp(self):
        self.pinion = make_pinion()
        self.gear2 = make_pinion(teeth_num=78, rpm=1500 / 3.1)

    def test_explicit_gear2_no_gear_ratio(self):
        gb = Transmission(gear1=self.pinion, gear2=self.gear2, oil_temp=65, reliability=0.999,
                          power=50e3, driving_machine='light shock',
                          driven_machine='moderate shock', SF=1.1, SH=1)
        self.assertIs(gb.gear2, self.gear2)

    def test_explicit_gear2_and_matching_gear_ratio(self):
        gb = Transmission(gear1=self.pinion, gear2=self.gear2, gear_ratio=78 / 25, oil_temp=65,
                          reliability=0.999, power=50e3, driving_machine='light shock',
                          driven_machine='moderate shock', SF=1.1, SH=1)
        self.assertIs(gb.gear2, self.gear2)

    def test_explicit_gear2_and_mismatched_gear_ratio_raises(self):
        with self.assertRaises(GearTypeError):
            Transmission(gear1=self.pinion, gear2=self.gear2, gear_ratio=5, oil_temp=65,
                        reliability=0.999, power=50e3, driving_machine='light shock',
                        driven_machine='moderate shock', SF=1.1, SH=1)

    def test_no_gear2_and_no_gear_ratio_raises(self):
        with self.assertRaises(GearTypeError):
            Transmission(gear1=self.pinion, oil_temp=65, reliability=0.999, power=50e3,
                        driving_machine='light shock', driven_machine='moderate shock',
                        SF=1.1, SH=1)

    def test_mismatched_gear_types_raises(self):
        helical = make_helical(teeth_num=78)
        with self.assertRaises(GearTypeError):
            Transmission(gear1=self.pinion, gear2=helical, oil_temp=65, reliability=0.999,
                        power=50e3, driving_machine='light shock',
                        driven_machine='moderate shock', SF=1.1, SH=1)


class TestTransmissionHelicalGears(unittest.TestCase):
    """Mirrors the helical_gearbox built in the worked example."""

    def setUp(self):
        self.helical = make_helical()
        self.gearbox = Transmission(
            gear1=self.helical, oil_temp=100, reliability=0.999, power=50e3,
            gear_ratio=2.5, driving_machine='uniform', driven_machine='uniform', SF=1, SH=1)

    def test_gear2_is_generated_from_gear_ratio(self):
        self.assertEqual(self.gearbox.gear2.teeth_num, 92)  # round(37*2.5)
        self.assertIsInstance(self.gearbox.gear2, HelicalGear)

    def test_Ko(self):
        self.assertEqual(self.gearbox.Ko, 1)

    def test_Ytheta_above_threshold(self):
        self.assertAlmostEqual(self.gearbox.Ytheta, 1.0843023255813953)

    def test_Yz(self):
        self.assertAlmostEqual(self.gearbox.Yz, 1.2529453254090528)

    def test_ZE(self):
        self.assertAlmostEqual(self.gearbox.ZE, 189.234939151512)

    def test_ZI_uses_helical_geometry_factor(self):
        self.assertAlmostEqual(self.gearbox.ZI, 0.194416669862086)

    def test_centers_distance_uses_tangent_modulus(self):
        self.assertAlmostEqual(self.gearbox.centers_distance, 137.81102153563063)

    def test_Yj_assigned_via_helical_table_lookup(self):
        self.assertAlmostEqual(self.gearbox.gear1.Yj, 0.5673721386666668)
        self.assertEqual(self.gearbox.gear1.Yj, self.gearbox.gear2.Yj)


class TestTransmissionTrainValue(unittest.TestCase):
    def test_train_value_with_plain_numbers(self):
        self.assertAlmostEqual(Transmission.train_value((10, 20), (50, 10)), 2.5)

    def test_train_value_with_gear_objects(self):
        pinion = make_pinion()
        gear2 = make_pinion(teeth_num=78, rpm=1500 / 3.1)
        self.assertAlmostEqual(
            Transmission.train_value((pinion, gear2)), -(25 / 78))

    def test_train_value_raises_on_non_iterable_pair(self):
        with self.assertRaises(TypeError):
            Transmission.train_value(5)


if __name__ == '__main__':
    unittest.main()
