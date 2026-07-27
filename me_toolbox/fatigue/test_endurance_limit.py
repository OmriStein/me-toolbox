import unittest
from math import sqrt

from me_toolbox.fatigue import EnduranceLimit


class TestEnduranceLimit(unittest.TestCase):

    def setUp(self):
        self.Sut = 700
        self.unmodified_Se = EnduranceLimit.unmodified_Se(self.Sut, 'steel')
        self.endurance_limit = EnduranceLimit(self.unmodified_Se, Sut=self.Sut,
                                              surface_finish='machined', rotating=True,
                                              max_normal_stress=50, max_bending_stress=200,
                                              stress_type='bending', temp=25, reliability=90,
                                              diameter=10)

    def test_unmodified_Se_steel(self):
        # below the 1400[MPa] divider -> 0.5*Sut
        self.assertAlmostEqual(EnduranceLimit.unmodified_Se(700, 'steel'), 0.5 * 700)
        # above the divider -> capped at 700
        self.assertAlmostEqual(EnduranceLimit.unmodified_Se(1500, 'steel'), 700)

    def test_unmodified_Se_iron(self):
        self.assertAlmostEqual(EnduranceLimit.unmodified_Se(300, 'iron'), 0.4 * 300)
        self.assertAlmostEqual(EnduranceLimit.unmodified_Se(500, 'iron'), 160)

    def test_unmodified_Se_aluminium(self):
        self.assertAlmostEqual(EnduranceLimit.unmodified_Se(200, 'aluminium'), 0.4 * 200)
        self.assertAlmostEqual(EnduranceLimit.unmodified_Se(400, 'aluminium'), 130)

    def test_unmodified_Se_copper_alloy(self):
        self.assertAlmostEqual(EnduranceLimit.unmodified_Se(200, 'copper alloy'), 0.4 * 200)
        self.assertAlmostEqual(EnduranceLimit.unmodified_Se(300, 'copper alloy'), 100)

    def test_A95_from_diameter(self):
        # A95 defaults to being computed from diameter when not given explicitly
        self.assertAlmostEqual(self.endurance_limit.A95, 0.01046 * 10 ** 2)

    def test_A95_from_width_height(self):
        el = EnduranceLimit(self.unmodified_Se, Sut=self.Sut, surface_finish='as forged',
                            rotating=False, max_normal_stress=10, max_bending_stress=200,
                            stress_type='shear', temp=300, reliability=99.9,
                            width=30, height=10)
        self.assertAlmostEqual(el.A95, 0.05 * 30 * 10)

    def test_A95_explicit_value_is_kept(self):
        el = EnduranceLimit(self.unmodified_Se, Sut=self.Sut, surface_finish='machined',
                            rotating=True, max_normal_stress=10, max_bending_stress=200,
                            stress_type='bending', temp=25, reliability=90, A95=12.34)
        self.assertAlmostEqual(el.A95, 12.34)

    def test_A95_raises_without_geometry(self):
        # not rotating (or no diameter) and no A95/width/height given -> can't compute A95
        self.assertRaises(ValueError, EnduranceLimit, self.unmodified_Se, self.Sut,
                          'ground', False, 10, 200, 'bending', 20, 50)

    def test_Ka_surface_finish(self):
        # Ka = a * Sut^b, Table for 'machined'/'cold-drawn' -> a=4.51, b=-0.265
        a, b = 4.51, -0.265
        self.assertAlmostEqual(self.endurance_limit.Ka, a * self.Sut ** b)
        self.assertAlmostEqual(self.endurance_limit.Ka, 0.7947408953320232)

    def test_Kb_rotating_round(self):
        # rotating round bar, de = diameter, de in [2.79, 51] -> 1.24*de^-0.107
        de = 10
        self.assertAlmostEqual(self.endurance_limit.Kb, 1.24 * de ** -0.107)
        self.assertAlmostEqual(self.endurance_limit.Kb, 0.9692184776895287)

    def test_Kb_axial_loading_is_one(self):
        # max_normal_stress > 0.85*max_bending_stress -> axial loading -> Kb=1
        el = EnduranceLimit(self.unmodified_Se, Sut=self.Sut, surface_finish='cold-drawn',
                            rotating=True, max_normal_stress=200, max_bending_stress=100,
                            stress_type='axial', temp=25, reliability=99, diameter=10)
        self.assertEqual(el.Kb, 1)

    def test_Kb_not_rotating_uses_A95(self):
        # not rotating -> de computed from A95 even though diameter is given
        el = EnduranceLimit(self.unmodified_Se, Sut=self.Sut, surface_finish='hot-rolled',
                            rotating=False, max_normal_stress=10, max_bending_stress=200,
                            stress_type='bending', temp=20, reliability=50, diameter=10)
        de = sqrt(el.A95 / 0.07658)
        self.assertAlmostEqual(el.Kb, 1.24 * de ** -0.107)
        self.assertAlmostEqual(el.Kb, 1.078144351445285)

    def test_Kc_load_types(self):
        types = {'bending': 1, 'axial': 0.85, 'torsion': 0.59, 'shear': 0.59, 'multiple': 1}
        for stress_type, factor in types.items():
            el = EnduranceLimit(self.unmodified_Se, Sut=self.Sut, surface_finish='machined',
                                rotating=True, max_normal_stress=10, max_bending_stress=200,
                                stress_type=stress_type, temp=25, reliability=90, diameter=10)
            self.assertAlmostEqual(el.Kc, factor)

    def test_Kd_temperature_factor(self):
        self.assertAlmostEqual(self.endurance_limit.Kd, EnduranceLimit.calc_kd(25))

    def test_calc_kd_interpolated(self):
        self.assertAlmostEqual(EnduranceLimit.calc_kd(400), 0.9)

    def test_Ke_reliability_factor(self):
        self.assertAlmostEqual(self.endurance_limit.Ke, EnduranceLimit.calc_ke(90))
        self.assertAlmostEqual(self.endurance_limit.Ke, 0.897)

    def test_calc_ke_interpolated(self):
        self.assertAlmostEqual(EnduranceLimit.calc_ke(99.99), 0.702)

    def test_Kf_is_always_one(self):
        self.assertEqual(self.endurance_limit.Kf, 1)

    def test_modified(self):
        el = self.endurance_limit
        expected = el.Ka * el.Kb * el.Kc * el.Kd * el.Ke * el.Kf * el.unmodified
        self.assertAlmostEqual(el.modified, expected)
        self.assertAlmostEqual(el.modified, 242.23168792524953)

    def test_get_factors_returns_all_marin_factors(self):
        el = self.endurance_limit
        factors = el.get_factors(verbose=False)
        self.assertEqual(len(factors), 6)
        expected = (el.Ka, el.Kb, el.Kc, el.Kd, el.Ke, el.Kf)
        for actual, exp in zip(factors, expected):
            self.assertAlmostEqual(actual, exp)


if __name__ == '__main__':
    unittest.main()
