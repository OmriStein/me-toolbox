import unittest
from math import inf

from me_toolbox.springs import HelicalTorsionSpring, Spring


class TestHelicalTorsionSpring(unittest.TestCase):
    def setUp(self):
        # values taken from
        # examples/springs_examples/HelicalToresionSpring_example.ipynb
        d = 1.829  # [mm]
        OD = 15.081  # [mm]
        D = OD - d  # [mm]
        pin = 10.16  # [mm]
        l1 = 25.4  # [mm]
        l2 = l1  # [mm]

        # music wire
        G = 81e3  # [MPa]
        E = 196.5e3  # [MPa]
        Sut = Spring.material_prop('music wire', d, metric=True, verbose=False)

        yield_percent = 0.45 / 0.577

        k = 525.11  # [Nmm/rad]
        Tmax = 851.27  # [Nmm]

        self.spring = HelicalTorsionSpring(max_moment=Tmax,
                                           wire_diameter=d,
                                           spring_diameter=D,
                                           leg1=l1,
                                           leg2=l2,
                                           ultimate_tensile_strength=Sut,
                                           yield_percent=yield_percent,
                                           shear_modulus=G,
                                           elastic_modulus=E,
                                           spring_rate=k,
                                           arbor_diameter=pin,
                                           shot_peened=False,
                                           density=7800)

        self.spring_no_arbor = HelicalTorsionSpring(max_moment=Tmax,
                                                     wire_diameter=d,
                                                     spring_diameter=D,
                                                     leg1=l1,
                                                     leg2=l2,
                                                     ultimate_tensile_strength=Sut,
                                                     yield_percent=yield_percent,
                                                     shear_modulus=G,
                                                     elastic_modulus=E,
                                                     spring_rate=k,
                                                     shot_peened=False,
                                                     density=7800)

        # gives a finite fatigue life (N != 0, N != inf)
        self.result_finite = self.spring.fatigue_analysis(max_moment=900, min_moment=112.979,
                                                           fatigue_percent=53, criterion='gerber',
                                                           reliability=50, verbose=False)

        # matches the notebook example - the safety factors are above 1 and the
        # spring is in the infinite-life regime (N == inf, Sf is None)
        self.result_inf = self.spring.fatigue_analysis(max_moment=564.896, min_moment=112.979,
                                                        fatigue_percent=53, criterion='gerber',
                                                        reliability=50, verbose=False)

    # --- construction -----------------------------------------------------

    def test_max_force(self):
        # max_force is derived in __init__ as max(max_moment/leg1, max_moment/leg2)
        self.assertAlmostEqual(self.spring.max_force,
                               max(self.spring.max_moment / self.spring.leg1,
                                   self.spring.max_moment / self.spring.leg2))

    # --- geometry -----------------------------------------------------------

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
        self.assertAlmostEqual(self.spring.active_coils, 4.656740583968519)

    def test_body_coils(self):
        self.assertAlmostEqual(self.spring.body_coils, 4.250005947231006)

    def test_partial_turn(self):
        self.assertAlmostEqual(self.spring.partial_turn, 90.00214100316228)

    def test_free_length(self):
        self.assertAlmostEqual(self.spring.free_length,
                               self.spring.wire_diameter * self.spring.body_coils)

    def test_loaded_length(self):
        self.assertAlmostEqual(self.spring.loaded_length, 10.059521754971021)

    def test_loaded_diameter(self):
        self.assertAlmostEqual(self.spring.loaded_diameter, 9.829950277552538)

    def test_clearance(self):
        # negative clearance means the spring interferes with the arbor once
        # loaded - this is the actual (if unfortunate) geometry produced by
        # the notebook's example numbers, not a hand-picked "good" case
        self.assertAlmostEqual(self.spring.clearance, -2.159049722447463)
        self.assertAlmostEqual(self.spring.clearance,
                               (self.spring.loaded_diameter - self.spring.wire_diameter)
                               - self.spring.arbor_diameter)

    def test_clearance_raises_without_arbor_diameter(self):
        self.assertRaises(KeyError, lambda: self.spring_no_arbor.clearance)

    # --- design checks --------------------------------------------------------

    def test_check_design_negative_clearance(self):
        # arbor_diameter is set and clearance is negative -> check_design returns False
        self.assertIs(self.spring.check_design(), False)

    def test_check_design_no_arbor(self):
        # arbor_diameter is None -> check_design short-circuits to None
        self.assertIsNone(self.spring_no_arbor.check_design())

    # --- material properties --------------------------------------------------

    def test_yield_strength(self):
        self.assertAlmostEqual(self.spring.yield_strength, 1579.8085353967158)
        self.assertAlmostEqual(self.spring.yield_strength,
                               self.spring.yield_percent * self.spring.ultimate_tensile_strength)

    # --- stress concentration factors ------------------------------------------

    def test_factor_Ki(self):
        self.assertAlmostEqual(self.spring.factor_Ki, 1.1145620039440975)

    def test_factor_Ko_equals_factor_Ki(self):
        # factor_Ko uses the exact same formula as factor_Ki (see docstring:
        # "we don't use it in the stress estimation... brought here for the
        # sake of completion") - pin down that they are indeed identical today
        self.assertAlmostEqual(self.spring.factor_Ko, self.spring.factor_Ki)

    # --- stresses ---------------------------------------------------------------

    def test_max_stress(self):
        self.assertAlmostEqual(self.spring.max_stress, 1579.5397197008394)

    def test_calc_max_stress(self):
        self.assertAlmostEqual(self.spring.calc_max_stress(100), 185.5509673430098)
        self.assertAlmostEqual(self.spring.calc_max_stress(self.spring.max_moment),
                               self.spring.max_stress)

    # --- angular deflection -------------------------------------------------------

    def test_max_angular_deflection(self):
        self.assertAlmostEqual(self.spring.max_angular_deflection, 1.6211270019614934)

    def test_calc_angular_deflection_total(self):
        self.assertAlmostEqual(self.spring.calc_angular_deflection(100), 0.19043628953933459)

    def test_calc_angular_deflection_partial(self):
        # total_deflection=False leaves out the leg-bending contribution, so it
        # must be strictly smaller than the total deflection for the same moment
        partial = self.spring.calc_angular_deflection(100, False)
        total = self.spring.calc_angular_deflection(100, True)
        self.assertAlmostEqual(partial, 0.17380297410104764)
        self.assertLess(partial, total)

    # --- weight -------------------------------------------------------------------

    def test_weight(self):
        self.assertAlmostEqual(self.spring.weight, 1.044685674717805)

    # --- static analysis ------------------------------------------------------------

    def test_static_analysis(self):
        self.assertAlmostEqual(self.spring.static_analysis(), 1.0001701860944194)
        self.assertAlmostEqual(self.spring.static_analysis(),
                               self.spring.yield_strength / self.spring.max_stress)

    # --- fatigue analysis -------------------------------------------------------------

    def test_fatigue_analysis_equal_moments_raises(self):
        self.assertRaises(ValueError, self.spring.fatigue_analysis,
                          max_moment=100, min_moment=100, fatigue_percent=53, reliability=50)

    def test_fatigue_analysis_finite_life(self):
        # FailureCriteria.get_safety_factors uses sympy internally for the
        # 'gerber' criterion, so nf comes back as a sympy Float - cast to
        # float before comparing (same pattern used for buckling/
        # natural_frequency in test_helical_compression_spring.py).
        nf, ns, N, Sf = self.result_finite
        self.assertAlmostEqual(float(nf), 1.09256874370552)
        self.assertAlmostEqual(ns, 0.9460165270184405)
        self.assertAlmostEqual(N, 8779.033603509599)
        self.assertAlmostEqual(Sf, 1362.1021884817087)

    def test_fatigue_analysis_infinite_life(self):
        nf, ns, N, Sf = self.result_inf
        self.assertAlmostEqual(float(nf), 1.77927152167822)
        self.assertAlmostEqual(ns, 1.5072064137763348)
        self.assertEqual(N, inf)
        self.assertIsNone(Sf)

    # --- natural frequency / spring rate ------------------------------------------------

    def test_natural_frequency_not_implemented(self):
        self.assertRaises(NotImplementedError, self.spring.natural_frequency)

    def test_calc_spring_rate(self):
        # calc_spring_rate is the inverse of the active_coils property, so
        # feeding the spring's own active_coils back in must reproduce the
        # spring_rate it was built with
        recomputed_rate = HelicalTorsionSpring.calc_spring_rate(
            self.spring.wire_diameter, self.spring.diameter,
            self.spring.active_coils, self.spring.elastic_modulus)
        self.assertAlmostEqual(recomputed_rate, self.spring.spring_rate)
