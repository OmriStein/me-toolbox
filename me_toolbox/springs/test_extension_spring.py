import unittest
from math import inf, pi

from me_toolbox.springs import ExtensionSpring, Spring


class TestExtensionSpring(unittest.TestCase):
    def setUp(self):
        # values taken from examples/springs_examples/HelicalExtensionSpring_example.ipynb
        d = 0.88  # [mm]
        D = 5.41  # [mm]
        r1 = 2.69  # [mm]
        r2 = 2.672  # [mm]

        # hard-drawn wire
        G = 80e3  # [MPa]
        E = 197.9e3  # [MPa]
        Sut = 1823.3  # [MPa]

        body_torsion_yield_percent = 0.45
        end_torsion_yield_percent = 0.4
        end_bending_yield_percent = 0.75

        k = 3.13  # [N/mm]
        Fmax = 22.24  # [N]
        Fi = 5.29  # [N]

        peened = False
        rho = 7800  # [kg/m^3]

        self.spring = ExtensionSpring(max_force=Fmax,
                                     initial_tension=Fi,
                                     wire_diameter=d,
                                     spring_diameter=D,
                                     hook_r1=r1, hook_r2=r2,
                                     ultimate_tensile_strength=Sut,
                                     body_shear_yield_percent=body_torsion_yield_percent,
                                     hook_normal_yield_percent=end_bending_yield_percent,
                                     hook_shear_yield_percent=end_torsion_yield_percent,
                                     shear_modulus=G, elastic_modulus=E,
                                     spring_rate=k,
                                     shot_peened=peened,
                                     density=rho)

        F_max = 22.24
        F_min = 6.67
        self.result = self.spring.fatigue_analysis(max_force=F_max, min_force=F_min,
                                                    criterion='gerber', reliability=50,
                                                    verbose=False)

    # --- geometry ---------------------------------------------------------

    def test_spring_index(self):
        self.assertAlmostEqual(self.spring.spring_index,
                               self.spring.diameter / self.spring.wire_diameter)

    def test_inside_diameter(self):
        self.assertAlmostEqual(self.spring.inside_diameter,
                               self.spring.diameter - self.spring.wire_diameter)

    def test_outside_diameter(self):
        self.assertAlmostEqual(self.spring.outside_diameter,
                               self.spring.diameter + self.spring.wire_diameter)

    def test_active_coils(self):
        self.assertAlmostEqual(self.spring.active_coils, 11.942266653793048)

    def test_body_coils(self):
        self.assertAlmostEqual(self.spring.body_coils,
                               self.spring.active_coils -
                               (self.spring.shear_modulus / self.spring.elastic_modulus))

    def test_free_length(self):
        self.assertAlmostEqual(self.spring.free_length, 20.0934594355299)

    def test_solid_length_not_implemented(self):
        # ExtensionSpring inherits solid_length from HelicalCompressionSpring but
        # explicitly disables it since it's meaningless for extension springs
        self.assertRaises(NotImplementedError, lambda: self.spring.solid_length)

    def test_Fsolid_not_implemented(self):
        self.assertRaises(NotImplementedError, lambda: self.spring.Fsolid)

    def test_total_coils_not_implemented(self):
        self.assertRaises(NotImplementedError, lambda: self.spring.total_coils)

    def test_buckling_not_implemented(self):
        self.assertRaises(NotImplementedError, self.spring.buckling, 'fixed-hinged')

    def test_calc_spring_rate_not_implemented(self):
        self.assertRaises(NotImplementedError, ExtensionSpring.calc_spring_rate, 1, 2, 3, 4)

    # --- design checks ------------------------------------------------------

    def test_check_spring_index(self):
        self.assertIs(self.spring._check_spring_index(), True)

    def test_check_active_coils(self):
        self.assertIs(self.spring._check_active_coils(), True)

    def test_check_design(self):
        self.assertIs(self.spring.check_design(), True)

    # --- material properties -------------------------------------------------

    def test_shear_yield_strength(self):
        self.assertAlmostEqual(self.spring.shear_yield_strength, 820.485)

    def test_shear_ultimate_strength(self):
        self.assertAlmostEqual(self.spring.shear_ultimate_strength,
                               0.67 * self.spring.ultimate_tensile_strength)

    def test_hook_normal_yield_strength(self):
        self.assertAlmostEqual(self.spring.hook_normal_yield_strength, 1367.475)

    def test_hook_shear_yield_strength(self):
        self.assertAlmostEqual(self.spring.hook_shear_yield_strength, 729.32)

    # --- hook stress-concentration factors -----------------------------------

    def test_hook_KA(self):
        self.assertAlmostEqual(self.spring.hook_KA, 1.1386699710863277)

    def test_hook_KB(self):
        self.assertAlmostEqual(self.spring.hook_KB, 1.1478494623655915)

    # --- stresses -------------------------------------------------------------

    def test_max_hook_normal_stress(self):
        self.assertAlmostEqual(self.spring.max_hook_normal_stress, 1060.4531303953718)

    def test_calc_normal_stress(self):
        self.assertAlmostEqual(self.spring.calc_normal_stress(self.spring.max_force),
                               self.spring.max_hook_normal_stress)

    def test_max_hook_shear_stress(self):
        self.assertAlmostEqual(self.spring.max_hook_shear_stress, 516.0705554778621)

    def test_max_body_shear_stress(self):
        self.assertAlmostEqual(self.spring.max_body_shear_stress, 560.0784754890378)

    # --- deflection -------------------------------------------------------------

    def test_max_deflection(self):
        self.assertAlmostEqual(self.spring.max_deflection,
                               (self.spring.max_force - self.spring.initial_tension) /
                               self.spring.spring_rate)

    def test_calc_deflection(self):
        self.assertAlmostEqual(self.spring.calc_deflection(10), 1.5047923322683707)

    # --- static analysis -------------------------------------------------------------

    def test_static_analysis(self):
        result = self.spring.static_analysis(verbose=False)
        self.assertAlmostEqual(result['n_body'], 1.4649464957273814)
        self.assertAlmostEqual(result['n_hook_normal'], 1.2895195089764697)
        self.assertAlmostEqual(result['n_hook_shear'], 1.4132176158058019)

    # --- fatigue analysis -------------------------------------------------------------

    def test_fatigue_analysis_body(self):
        # FailureCriteria.get_safety_factors uses sympy internally for some
        # criteria (e.g. 'gerber'), so nf/ns can come back as sympy Float -
        # cast to float before comparing (same pattern as buckling/
        # natural_frequency in test_helical_compression_spring.py).
        body = self.result['body']
        self.assertAlmostEqual(float(body['nf']), 1.18933657586707)
        self.assertAlmostEqual(float(body['ns']), 1.6100536911490835)
        self.assertAlmostEqual(float(body['N']), 778907.1129858237)
        self.assertAlmostEqual(float(body['Sf']), 279.27263758118505)

    def test_fatigue_analysis_hook_normal(self):
        hook_normal = self.result['hook_normal']
        self.assertAlmostEqual(float(hook_normal['nf']), 1.04918175235621)
        self.assertAlmostEqual(float(hook_normal['ns']), 1.2895195089764697)
        self.assertAlmostEqual(float(hook_normal['N']), 196286.0903554985)
        self.assertAlmostEqual(float(hook_normal['Sf']), 596.8154208328335)

    def test_fatigue_analysis_hook_shear(self):
        hook_shear = self.result['hook_shear']
        self.assertAlmostEqual(float(hook_shear['nf']), 1.29075726019318)
        self.assertAlmostEqual(float(hook_shear['ns']), 1.4132176158058019)
        self.assertEqual(hook_shear['N'], inf)
        self.assertIsNone(hook_shear['Sf'])

    # --- weight & natural frequency -------------------------------------------------------------

    def test_weight_raises_due_to_total_coils(self):
        # HelicalCompressionSpring.weight() reads self.total_coils, which
        # ExtensionSpring deliberately overrides to raise NotImplementedError.
        # As a result weight() is unusable on ExtensionSpring even though it's
        # not itself overridden - this looks like a real (if minor) bug in the
        # library rather than intentional behavior, but the tests pin down
        # what the code does today.
        self.assertRaises(NotImplementedError, lambda: self.spring.weight)

    def test_natural_frequency(self):
        # natural_frequency() uses sympy.sqrt internally so the values are
        # sympy Float objects; cast to float before comparing (see
        # test_helical_compression_spring.py for the same pattern).
        result = self.spring.natural_frequency(density=7800, working_frequency=0.5)
        self.assertAlmostEqual(float(result['fixed-fixed']), 0.907411342896479)
        self.assertAlmostEqual(float(result['fixed-free']), 0.453705671448239)
