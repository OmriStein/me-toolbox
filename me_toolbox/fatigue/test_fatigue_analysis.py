import unittest
from math import sqrt, inf

from me_toolbox.fatigue import FatigueAnalysis


class TestFatigueAnalysis(unittest.TestCase):

    def setUp(self):
        # a 'multiple' stress-type analysis (combined bending/normal/torsion), ductile material
        self.fa_multiple = FatigueAnalysis(
            modified_endurance_limit=242.23168792524953,
            stress_type='multiple', ductile=True,
            ultimate_tensile_strength=700, yield_strength=525,
            Kf_bending=1.2, Kf_normal=1.1, Kf_torsion=1.05,
            alt_bending_stress=50, alt_normal_stress=30, alt_torsion_stress=20,
            mean_bending_stress=80, mean_normal_stress=40, mean_torsion_stress=15)

        # a plain 'bending' stress-type analysis, landing the reversible stress
        # inside the High Cycle Fatigue range so num_of_cycles returns a real value
        self.fa_bending = FatigueAnalysis(
            modified_endurance_limit=242.23168792524953,
            stress_type='bending', ductile=True,
            ultimate_tensile_strength=700, yield_strength=525,
            Kf_bending=1.4,
            alt_bending_stress=180,
            mean_bending_stress=250)

        # a 'torsion' stress-type analysis, to exercise the shear strength corrections
        self.fa_torsion = FatigueAnalysis(
            modified_endurance_limit=200,
            stress_type='torsion', ductile=True,
            ultimate_tensile_strength=700, yield_strength=525,
            Kf_torsion=1.0,
            alt_torsion_stress=80,
            mean_torsion_stress=60)

        # a negative mean-stress case (second quadrant of the alt-mean stress plane)
        self.fa_negative_mean = FatigueAnalysis(
            modified_endurance_limit=200,
            stress_type='bending', ductile=True,
            ultimate_tensile_strength=700, yield_strength=525,
            Kf_bending=1.0,
            alt_bending_stress=150,
            mean_bending_stress=-50)

    def test_calc_kf(self):
        q, Kt = 0.7, 2.35
        self.assertAlmostEqual(FatigueAnalysis.calc_kf(q, Kt), 1 + q * (Kt - 1))

    def test_calc_thread_kf_low_grade(self):
        self.assertEqual(FatigueAnalysis.calc_thread_kf(4.6, 'Rolled Threads'), 2.2)
        self.assertEqual(FatigueAnalysis.calc_thread_kf(4.6, 'Cut Threads'), 2.8)

    def test_calc_thread_kf_high_grade(self):
        self.assertEqual(FatigueAnalysis.calc_thread_kf(8.8, 'Rolled Threads'), 3)
        self.assertEqual(FatigueAnalysis.calc_thread_kf(8.8, 'Cut Threads'), 3.8)

    def test_calc_thread_kf_bad_manufacturing_raises(self):
        self.assertRaises(ValueError, FatigueAnalysis.calc_thread_kf, 4.6, 'Bad Method')

    def test_calc_thread_kf_bad_grade_raises(self):
        self.assertRaises(ValueError, FatigueAnalysis.calc_thread_kf, 6.0, 'Rolled Threads')

    def test_alt_eq_stress_multiple(self):
        fa = self.fa_multiple
        corrected_bending = fa.Kf_bending * fa.alt_bending_stress
        corrected_normal = fa.Kf_normal * (fa.alt_normal_stress / 0.85)
        corrected_torsion = fa.Kf_torsion * fa.alt_torsion_stress
        expected = sqrt((corrected_bending + corrected_normal) ** 2 + 3 * corrected_torsion ** 2)
        self.assertAlmostEqual(float(fa.alt_eq_stress), expected)
        self.assertAlmostEqual(float(fa.alt_eq_stress), 105.30474806673213)

    def test_mean_eq_stress_multiple_ductile(self):
        # ductile material -> Kf factors are not applied to the mean stresses
        fa = self.fa_multiple
        expected = sqrt((fa.mean_bending_stress + fa.mean_normal_stress) ** 2
                        + 3 * fa.mean_torsion_stress ** 2)
        self.assertAlmostEqual(float(fa.mean_eq_stress), expected)
        self.assertAlmostEqual(float(fa.mean_eq_stress), 122.78029157808675)

    def test_mean_eq_stress_multiple_not_ductile_applies_Kf(self):
        # non-ductile material -> the Kf factors ARE applied to the mean stresses too
        fa = FatigueAnalysis(
            modified_endurance_limit=242.23168792524953,
            stress_type='multiple', ductile=False,
            ultimate_tensile_strength=700, yield_strength=525,
            Kf_bending=1.2, Kf_normal=1.1, Kf_torsion=1.05,
            mean_bending_stress=80, mean_normal_stress=40, mean_torsion_stress=15)
        cb = 1.2 * 80
        cn = 1.1 * 40
        ct = 1.05 * 15
        expected = sqrt((cb + cn) ** 2 + 3 * ct ** 2)
        self.assertAlmostEqual(float(fa.mean_eq_stress), expected)

    def test_alt_eq_stress_bending(self):
        fa = self.fa_bending
        self.assertAlmostEqual(fa.alt_eq_stress, fa.Kf_bending * fa.alt_bending_stress)
        self.assertAlmostEqual(fa.alt_eq_stress, 251.99999999999997)

    def test_mean_eq_stress_bending(self):
        fa = self.fa_bending
        self.assertAlmostEqual(fa.mean_eq_stress, fa.mean_bending_stress)
        self.assertEqual(fa.mean_eq_stress, 250)

    def test_alt_eq_stress_torsion(self):
        fa = self.fa_torsion
        self.assertAlmostEqual(fa.alt_eq_stress, fa.Kf_torsion * fa.alt_torsion_stress)

    def test_shear_ultimate_strength(self):
        fa = self.fa_torsion
        self.assertAlmostEqual(fa.shear_ultimate_strength, 0.67 * fa.Sut)

    def test_shear_yield_stress(self):
        fa = self.fa_torsion
        # uses sympy.sqrt internally -> wrap in float() (see test_helical_compression_spring.py)
        self.assertAlmostEqual(float(fa.shear_yield_stress), fa.Sy / sqrt(3))

    def test_modified_goodman_bending(self):
        fa = self.fa_bending
        self.assertAlmostEqual(fa.modified_goodman, 0.7155792899004539)

    def test_soderberg_bending(self):
        fa = self.fa_bending
        self.assertAlmostEqual(fa.soderberg, 0.6594058198608961)

    def test_gerber_bending(self):
        fa = self.fa_bending
        # gerber uses sympy.sqrt internally -> returns a sympy Float
        self.assertAlmostEqual(float(fa.gerber), 0.868710670171752)

    def test_ASME_elliptic_bending(self):
        fa = self.fa_bending
        self.assertAlmostEqual(float(fa.ASME_elliptic), 0.909154827058747)

    def test_langer_static_yield_bending(self):
        fa = self.fa_bending
        self.assertAlmostEqual(fa.langer_static_yield, 1.045816733067729)

    def test_torsion_criteria_use_shear_corrected_strengths(self):
        # for 'torsion'/'shear' stress types, modified_goodman/gerber/ASME use the shear
        # ultimate strength and soderberg/langer use the shear yield strength
        fa = self.fa_torsion
        self.assertAlmostEqual(fa.modified_goodman, 1.8941841680129239)
        # soderberg uses shear_yield_stress internally, which is a sympy expression
        # (Sy/sqrt(3).evalf()), so wrap in float() (see test_helical_compression_spring.py)
        self.assertAlmostEqual(float(fa.soderberg), 1.67238437121863)
        self.assertAlmostEqual(fa.langer_static_yield, 3.35)

    def test_criteria_return_none_for_negative_mean_stress(self):
        fa = self.fa_negative_mean
        self.assertIsNone(fa.modified_goodman)
        self.assertIsNone(fa.soderberg)
        self.assertIsNone(fa.gerber)
        self.assertIsNone(fa.ASME_elliptic)

    def test_langer_still_works_for_negative_mean_stress(self):
        fa = self.fa_negative_mean
        self.assertAlmostEqual(fa.langer_static_yield,
                               fa.Sy / (fa.alt_eq_stress - fa.mean_eq_stress))
        self.assertAlmostEqual(fa.langer_static_yield, 2.625)

    def test_get_safety_factors_negative_mean_uses_fatigue_alternative(self):
        fa = self.fa_negative_mean
        fatigue_sf, static_sf = fa.get_safety_factors('modified goodman')
        self.assertAlmostEqual(fatigue_sf, fa.Se / fa.alt_eq_stress)
        self.assertAlmostEqual(static_sf, 2.625)

    def test_get_safety_factors_modified_goodman(self):
        fa = self.fa_bending
        nF, nl = fa.get_safety_factors('modified goodman')
        self.assertAlmostEqual(nF, fa.modified_goodman)
        self.assertAlmostEqual(nl, fa.langer_static_yield)

    def test_calc_Sm_low_Sut(self):
        # Sut < 482.633[MPa] (70[kPsi]) -> Sm = 0.9*Sut
        self.assertAlmostEqual(FatigueAnalysis.calc_Sm(300), 0.9 * 300)

    def test_calc_Sm_high_Sut(self):
        # Sut > 1378.95[MPa] (200[kPsi]) -> Sm = 0.75*Sut
        self.assertAlmostEqual(FatigueAnalysis.calc_Sm(1500), 0.75 * 1500)

    def test_calc_Sm_mid_range(self):
        self.assertAlmostEqual(FatigueAnalysis.calc_Sm(700), 588.808246511786)

    def test_Sm_stress_property(self):
        fa = self.fa_bending
        self.assertAlmostEqual(fa.Sm_stress, FatigueAnalysis.calc_Sm(fa.Sut))

    def test_num_of_cycles_infinite_life(self):
        # for the 'multiple' stress case the reversible stress falls below Se
        # -> infinite life (N=inf, Sf=None)
        N, Sf = self.fa_multiple.num_of_cycles()
        self.assertEqual(N, inf)
        self.assertIsNone(Sf)

    def test_num_of_cycles_high_cycle_fatigue(self):
        # the bending case lands the reversible stress inside the HCF range (Se < rev < Sm)
        N, Sf = self.fa_bending.num_of_cycles()
        self.assertAlmostEqual(N, 23666.636127990758)
        self.assertAlmostEqual(Sf, 392.0)

    def test_calc_num_of_cycles_mean_greater_than_Sut(self):
        # mean_stress >= Sut -> undefined reversible stress -> (0, None)
        N, Sf = FatigueAnalysis.calc_num_of_cycles(800, 50, 200, 700, 525)
        self.assertEqual(N, 0)
        self.assertIsNone(Sf)

    def test_miner_rule(self):
        # values from examples/fatigue_examples/FatigueAnalysis_example2.py, chosen so that
        # every group resolves to either HCF or infinite life (never the unresolved branch
        # logged as a known bug in TODO.md for miner_rule)
        stress_groups = [[2, 700, 500], [5, 400, 540], [3, 900, -200]]
        N_total = self.fa_bending.miner_rule(stress_groups, Sut=1500, Se=750, Sy=1250,
                                             alt_mean=True, freq=True)
        self.assertAlmostEqual(N_total, 1461.1512576402367)
        # the second group's reversible stress (625) is below Se(750) -> infinite life
        self.assertEqual(stress_groups[1][-1], inf)


if __name__ == '__main__':
    unittest.main()
