import unittest
from math import inf

from me_toolbox.springs import HelicalCompressionSpring, Spring

class TestHelicalCompressionSpring(unittest.TestCase):
    def setUp(self):
        d = 6  # [mm]
        D = 50  # [mm]
        ends = 'squared and ground'
        # music wire
        G = 75e3  # [MPa]
        E = 205e3  # [MPa]
        Sut = Spring.material_prop('music wire', d, metric=True, verbose=False)
        yield_percent = 0.45
        k = 6  # [N/mm]
        Fmax = 500  # [N]
        Fmin = 100  # [N]
        removed_set = False
        peened = True
        rho = 7800  # [kg/m^3]
        omega = None
        anchors = 'fixed-hinged'
        z = 0.25
        self.spring = HelicalCompressionSpring(max_force=Fmax,
                                               wire_diameter=d,
                                               spring_diameter=D,
                                               ultimate_tensile_strength=Sut,
                                               shear_yield_percent=yield_percent,
                                               shear_modulus=G,
                                               elastic_modulus=E,
                                               end_type=ends,
                                               spring_rate=k,
                                               set_removed=removed_set,
                                               shot_peened=peened,
                                               density=rho,
                                               zeta=z)

        self.result = self.spring.fatigue_analysis(max_force=Fmax,
                                                   min_force=Fmin,
                                                   reliability=99.999,
                                                   verbose=False)

        Fmax = 1000
        self.result2 = self.spring.fatigue_analysis(max_force=Fmax,
                                                    min_force=Fmin,
                                                    reliability=99.999,
                                                    verbose=False)

        self.result3 = self.spring.natural_frequency(7800, 0.0005)

    def test_check_zeta(self):
        self.assertIs(self.spring._check_zeta(),True)

    def test_check_active_coils(self):
        self.assertIs(self.spring._check_active_coils(),False)

    def test_check_spring_index(self):
        self.assertIs(self.spring._check_spring_index(),True)

    def test_check_design(self):
        self.assertIs(self.spring.check_design(),False)

    def test_free_length(self):
        self.assertAlmostEqual(self.spring.free_length,212.67182949430764)

    def test_solid_length(self):
        self.assertAlmostEqual(self.spring.solid_length,108.50516282764099)

    def test_Fsolid(self):
        self.assertAlmostEqual(self.spring.Fsolid, 625)

    def test_active_coils(self):
        self.assertAlmostEqual(self.spring.active_coils, 16.08419380460683)

    def test_end_coils(self):
        self.assertAlmostEqual(self.spring.end_coils, 2)

    def test_total_coils(self):
        self.assertAlmostEqual(self.spring.total_coils, 18.08419380460683)

    def test_pitch(self):
        self.assertAlmostEqual(self.spring.pitch, 12.47633744855967)

    def test_shear_yield_strength(self):
        self.assertAlmostEqual(self.spring.shear_yield_strength, 767.3072912399637)

    def test_factor_Ks(self):
        self.assertAlmostEqual(self.spring.factor_Ks, 1.06)

    def test_factor_Kw(self):
        self.assertAlmostEqual(self.spring.factor_Kw, 1.1760727272727274)

    def test_factor_KB(self):
        self.assertAlmostEqual(self.spring.factor_KB, 1.164835164835165)

    def test_max_shear_stress(self):
        self.assertAlmostEqual(self.spring.max_shear_stress, 346.62553329818724)

    def test_max_deflection(self):
        self.assertAlmostEqual(self.spring.max_deflection, 83.33333333333336)

    def test_weight(self):
        self.assertAlmostEqual(self.spring.weight, 0.6264782740619925)

    def test_static_analysis_default(self):
        self.assertAlmostEqual(self.spring.static_analysis(), 2.213649075239595)

    def test_static_analysis_solid_true(self):
        self.assertAlmostEqual(self.spring.static_analysis(solid=True), 1.7709192601916766)

    def test_fatigue_analysis(self):
        self.assertEqual(self.result, (1.6801675569311425, 2.2136490752395956, inf, None))
    def test_fatigue_analysis_nf_less_then_one(self):
        self.assertEqual(self.result2, (0.7915777277160205, 1.1068245376197978, 97221.28061023176, 468.23730587509914))

    def test_buckling(self):
        # buckling() and natural_frequency() use sympy.sqrt internally, so their results
        # are sympy Float objects; cast to float so assertAlmostEqual's round(diff, places)
        # check works the same way it does for plain Python floats
        _, free_length = self.spring.buckling('fixed-hinged')
        self.assertAlmostEqual(float(free_length), 190.139768448083)

    def test_natural_frequency_fixed_fixed(self):
        self.assertAlmostEqual(float(self.result3['fixed-fixed']), 0.0520715383736995)

    def test_natural_frequency_fixed_free(self):
        self.assertAlmostEqual(float(self.result3['fixed-free']), 0.0260357691868497)

    def test_calc_spring_rate(self):
        self.assertAlmostEqual(self.spring.calc_spring_rate(6, 50, 18, 'squared and ground', 75e3), 6.031572676727561)

    def test_calc_spring_rate_key_error(self):
        self.assertRaises(KeyError, self.spring.calc_spring_rate,6, 50, 18, 'test', 75e3)