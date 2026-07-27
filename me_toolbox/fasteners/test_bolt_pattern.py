from unittest import TestCase
from math import pi

import numpy as np
from numpy.testing import assert_allclose

from me_toolbox.fasteners import Bolt, ThreadedFastener, BoltPattern
from me_toolbox.fatigue import EnduranceLimit, FatigueAnalysis


class TestBoltPattern(TestCase):
    """Tests built around the eccentric bolt-group example in
    examples/fasteners_examples/BoltPattern_example.ipynb: two M10 fasteners and one M5
    fastener sharing two clamped layers, loaded by an in-plane shear force whose line of
    action is offset 100mm out of the fasteners' plane -- producing both direct/torque
    shear and bending-induced tension across the pattern.
    """

    def setUp(self):
        layers = [[5, 207e3], [10, 207e3]]

        M10_Sy, M10_Sut, M10_Sp = Bolt.get_strength_prop(10, '9.8')
        self.M10 = Bolt(10, 1.5, 33, 26, M10_Sy, M10_Sut, M10_Sp, 207e3)
        self.M10_fastener = ThreadedFastener(self.M10, layers, nut=True, preload=32062.5)

        M5_Sy, M5_Sut, M5_Sp = Bolt.get_strength_prop(5, '9.8')
        self.M5 = Bolt(5, 0.8, 23, 16, M5_Sy, M5_Sut, M5_Sp, 207e3)
        self.M5_fastener = ThreadedFastener(self.M5, layers, nut=True, preload=7850)

        self.fasteners = [self.M10_fastener, self.M10_fastener, self.M5_fastener]
        self.fasteners_locations = [[20, 45, 0], [-20, 45, 0], [0, 15, 0]]
        self.force = [0, -8500, 0]
        self.force_location = [0, 0, 100]
        self.axis_of_rotation = [[0, 0], [1, 0]]

        self.pattern = BoltPattern(self.fasteners, self.fasteners_locations, self.force,
                                    self.force_location, self.axis_of_rotation, 'shank')

    # ---- stiffness ----------------------------------------------------

    def test_fasteners_stiffness(self):
        expected = [f.fastener_stiffness for f in self.fasteners]
        assert_allclose(self.pattern.fasteners_stiffness, expected)

    def test_total_stiffness(self):
        expected = [f.member_stiffness + f.bolt_stiffness for f in self.fasteners]
        assert_allclose(self.pattern.total_stiffness, expected)

    # ---- shear area -----------------------------------------------------

    def test_bolt_shear_area_shank(self):
        # shear_location='shank' -> nominal (shank) area of each bolt
        expected = [0.25 * pi * f.bolt.diameter ** 2 for f in self.fasteners]
        assert_allclose(self.pattern.bolt_shear_area, expected)

    def test_bolt_shear_area_thread(self):
        self.pattern.shear_location = 'thread'
        expected = [f.bolt.stress_area for f in self.fasteners]
        assert_allclose(self.pattern.bolt_shear_area, expected)

    def test_bolt_shear_area_invalid_location_raises(self):
        self.pattern.shear_location = 'invalid'
        with self.assertRaises(ValueError):
            _ = self.pattern.bolt_shear_area

    # ---- shear distribution ---------------------------------------------

    def test_center_of_rotation(self):
        # area-weighted centroid of the fastener locations
        areas = np.array(self.pattern.bolt_shear_area)
        locations = np.array(self.fasteners_locations, dtype=float)
        expected = np.average(locations, axis=0, weights=areas)
        assert_allclose(self.pattern.center_of_rotation, expected, atol=1e-9)

    def test_direct_shear_force(self):
        # in-plane force split between fasteners in proportion to shear area
        areas = np.array(self.pattern.bolt_shear_area)
        force = np.array(self.force, dtype=float)
        force[2] = 0
        expected = [force * area / areas.sum() for area in areas]
        assert_allclose(self.pattern.direct_shear_force, expected)

    def test_torque_shear_force_is_zero_for_this_geometry(self):
        # the force's moment about the center of rotation here is entirely about
        # the x-axis (it becomes bending_normal_load, i.e. tension), it has no
        # z-component, so no in-plane twisting shear force results
        for f in self.pattern.torque_shear_force:
            assert_allclose(f, [0, 0, 0], atol=1e-9)

    def test_total_shear_force_equals_direct_shear_force(self):
        # torque_shear_force is ~0 for this geometry (see previous test), so total
        # shear force collapses to the direct shear force alone
        assert_allclose(self.pattern.total_shear_force, self.pattern.direct_shear_force)

    def test_shear_stress(self):
        expected = [np.linalg.norm(f) / a for f, a in
                    zip(self.pattern.total_shear_force, self.pattern.bolt_shear_area)]
        assert_allclose(self.pattern.shear_stress, expected)

    def test_eccentric_shear_square_pattern(self):
        """Dedicated scenario (four identical bolts at the corners of a square, loaded
        by a purely in-plane, off-center shear force) producing a non-zero
        torque_shear_force -- exercising the moment-distribution formula that
        test_torque_shear_force_is_zero_for_this_geometry cannot, since that scenario's
        eccentricity happens to produce zero twisting moment."""
        fasteners = [self.M10_fastener] * 4
        locations = [[30, 30, 0], [-30, 30, 0], [-30, -30, 0], [30, -30, 0]]
        force = [0, -4000, 0]
        force_location = [80, 0, 0]
        pattern = BoltPattern(fasteners, locations, force, force_location,
                               [[0, 0], [0, 1]], 'shank')

        area = self.M10.nominal_area

        # symmetric square of identical bolts -> center of rotation is the centroid
        assert_allclose(pattern.center_of_rotation, [0, 0, 0], atol=1e-9)

        expected_direct = [np.array([0, -1000, 0], dtype=float)] * 4
        assert_allclose(pattern.direct_shear_force, expected_direct)

        G = np.array(pattern.center_of_rotation)
        r = [np.array(loc, dtype=float) - G for loc in locations]
        torque = np.cross(np.array(force_location, dtype=float) - G, np.array(force, dtype=float))
        torque[0] = 0
        torque[1] = 0
        b = sum(area * np.linalg.norm(ri) ** 2 for ri in r)
        expected_torque = [np.cross(torque, ri) * area / b for ri in r]
        assert_allclose(pattern.torque_shear_force, expected_torque, atol=1e-9)

        expected_total = [d + t for d, t in zip(expected_direct, expected_torque)]
        assert_allclose(pattern.total_shear_force, expected_total, atol=1e-9)

        expected_stress = [np.linalg.norm(f) / area for f in expected_total]
        assert_allclose(pattern.shear_stress, expected_stress, atol=1e-9)
        # bolts diagonally aligned with the twist see higher combined shear stress
        # than the other two (direct and torque shear partially cancel for them)
        self.assertAlmostEqual(pattern.shear_stress[0], 34.21728461660395)
        self.assertAlmostEqual(pattern.shear_stress[1], 17.49900376552139)
        self.assertAlmostEqual(pattern.shear_stress[2], 17.49900376552139)
        self.assertAlmostEqual(pattern.shear_stress[3], 34.21728461660395)

    # ---- normal/tension distribution --------------------------------------

    def test_neutral_point(self):
        # stiffness-weighted centroid of the fastener locations
        stiffness = np.array(self.pattern.total_stiffness)
        locations = np.array(self.fasteners_locations, dtype=float)
        expected = np.average(locations, axis=0, weights=stiffness)
        assert_allclose(self.pattern.neutral_point, expected, atol=1e-9)

    def test_direct_normal_load(self):
        # no z-component in self.force here, so pure-tension load is zero for all bolts
        stiffness = np.array(self.pattern.total_stiffness)
        expected = [[0, 0, self.force[2] * k / stiffness.sum()] for k in stiffness]
        assert_allclose(self.pattern.direct_normal_load, expected, atol=1e-9)

    def test_direct_normal_load_pure_axial_force(self):
        """With a purely axial (out-of-plane) external force -- following
        BoltPattern_example2.ipynb's geometry -- direct_normal_load should be non-zero
        and split among fasteners in proportion to stiffness, while direct_shear_force
        and torque_shear_force should vanish entirely (no in-plane force component)."""
        thickness, elastic = [10, 50], [207e3, 76e3]
        layers = [[t, e] for t, e in zip(thickness, elastic)]

        M10_Sy, M10_Sut, M10_Sp = Bolt.get_strength_prop(10, '5.8')
        M10 = Bolt(10, 1.5, 33, 26, M10_Sy, M10_Sut, M10_Sp, 207e3)
        M10_fastener = ThreadedFastener(M10, layers, nut=False, preload=18750)

        M8_Sy, M8_Sut, M8_Sp = Bolt.get_strength_prop(8, '5.8')
        M8 = Bolt(8, 1.25, 30, 22, M8_Sy, M8_Sut, M8_Sp, 207e3)
        M8_fastener = ThreadedFastener(M8, layers, nut=False, preload=11812.5)

        fasteners = [M10_fastener, M10_fastener, M8_fastener, M8_fastener]
        locations = [[-20, 20, 0], [-20, -20, 0], [-61, 0, 0], [-85, 0, 0]]
        force = [0, 0, -8140]
        force_location = [40, 0, 0]
        axis_of_rotation = [[0, 0], [0, 1]]

        pattern = BoltPattern(fasteners, locations, force, force_location,
                               axis_of_rotation, 'shank')

        stiffness = np.array(pattern.total_stiffness)
        expected = [[0, 0, force[2] * k / stiffness.sum()] for k in stiffness]
        assert_allclose(pattern.direct_normal_load, expected, atol=1e-9)
        self.assertTrue(all(load[2] < 0 for load in pattern.direct_normal_load))

        for f in pattern.direct_shear_force:
            assert_allclose(f, [0, 0, 0], atol=1e-9)
        for f in pattern.torque_shear_force:
            assert_allclose(f, [0, 0, 0], atol=1e-9)

    def test_bending_normal_load(self):
        expected = [
            [0, 0, 9272.059608812322],
            [0, 0, 9272.059608812322],
            [0, 0, 1034.3090137927402],
        ]
        for actual, exp in zip(self.pattern.bending_normal_load, expected):
            assert_allclose(actual, exp, atol=1e-6)

    def test_fastener_load(self):
        expected = [9272.059608812322, 9272.059608812322, 1034.3090137927402]
        assert_allclose(self.pattern.fastener_load, expected)

    def test_bolt_load(self):
        expected = [34433.76753114912, 34433.76753114912, 8044.976035793829]
        assert_allclose(self.pattern.bolt_load, expected)

    def test_normal_stress(self):
        expected = [593.7921518825638, 593.7921518825638, 567.2447552563]
        assert_allclose(self.pattern.normal_stress, expected)

    def test_equivalent_stresses(self):
        expected = [599.6082020623708, 599.6082020623708, 573.3301742529543]
        assert_allclose(self.pattern.equivalent_stresses, expected)

    # ---- static safety factors ---------------------------------------------

    def test_load_safety_factor_min(self):
        self.assertAlmostEqual(self.pattern.load_safety_factor(), 2.374568838072321)

    def test_load_safety_factor_list(self):
        expected = [2.374568838072321, 2.374568838072321, 7.01961279892866]
        assert_allclose(self.pattern.load_safety_factor(minimal_value=False), expected)

    def test_separation_safety_factor_min(self):
        self.assertAlmostEqual(self.pattern.separation_safety_factor(), 4.646205774519905)

    def test_separation_safety_factor_list(self):
        expected = [4.646205774519905, 4.646205774519905, 9.352664801418287]
        assert_allclose(self.pattern.separation_safety_factor(minimal_value=False), expected)

    def test_proof_safety_factor_min(self):
        self.assertAlmostEqual(self.pattern.proof_safety_factor(), 1.0840412085163362)

    def test_proof_safety_factor_list(self):
        expected = [1.0840412085163362, 1.0840412085163362, 1.1337271770964192]
        assert_allclose(self.pattern.proof_safety_factor(minimal_value=False), expected)

    # ---- variable loading / fatigue -----------------------------------------

    def test_variable_loading_stresses(self):
        Fmin = [0, -6500, 0]
        Fmax = [0, -8500, 0]
        result = self.pattern.variable_loading_stresses(Fmin, Fmax)
        assert_allclose(result['alt_normal_stress'],
                         [4.810736160067165, 4.810736160067165, 1.6173650152466053])
        assert_allclose(result['alt_shear_stress'],
                         [5.658842421045165, 5.658842421045165, 5.658842421045165])
        assert_allclose(result['mean_normal_stress'],
                         [588.9814157224966, 588.9814157224966, 565.6273902410534])
        assert_allclose(result['mean_shear_stress'],
                         [42.44131815783876, 42.44131815783876, 42.44131815783876])

    def test_variable_loading_stresses_restores_force(self):
        # the method temporarily overwrites self.force to compute min/max stresses,
        # it must restore the original force afterwards
        Fmin = [0, -6500, 0]
        Fmax = [0, -8500, 0]
        self.pattern.variable_loading_stresses(Fmin, Fmax)
        self.assertEqual(self.pattern.force, self.force)

    def _build_endurance_limits(self):
        M10_unmodified_Se = EnduranceLimit.unmodified_Se(self.M10.tensile_strength, 'steel')
        M5_unmodified_Se = EnduranceLimit.unmodified_Se(self.M5.tensile_strength, 'steel')
        M10_Se = self.M10.endurance_limit(M10_unmodified_Se, surface_finish='cold-drawn',
                                           temp=300, reliability=0.9)
        M5_Se = self.M5.endurance_limit(M5_unmodified_Se, surface_finish='cold-drawn',
                                         temp=300, reliability=0.9)

        Kf = FatigueAnalysis.calc_thread_kf(9.8, 'Rolled Threads')
        self.M10.Kf = Kf
        self.M5.Kf = Kf

        return [M10_Se, M10_Se, M5_Se]

    def test_variable_equivalent_stresses(self):
        """Regression test for variable_equivalent_stresses: it used to call
        FatigueAnalysis with a mismatched/broken signature and crashed for every
        caller. It was fixed to pass modified_endurance_limit, stress_type='multiple',
        ultimate_tensile_strength, yield_strength, Kf_normal/Kf_torsion etc. correctly,
        so this must run end to end without raising and produce the expected
        mean/alternating equivalent stresses."""
        Fmin = [0, -6500, 0]
        Fmax = [0, -8500, 0]
        endurance_limits = self._build_endurance_limits()

        result = self.pattern.variable_equivalent_stresses(endurance_limits, Fmin, Fmax)

        self.assertEqual(len(result), 3)
        # FatigueAnalysis computes these via sympy.sqrt, so the results are sympy Float
        # objects with ~15 significant digits of precision rather than a raw float64 --
        # cast to float before comparing to avoid spurious precision mismatches.
        self.assertAlmostEqual(float(result[0]['mean']), 593.551096812567, places=6)
        self.assertAlmostEqual(float(result[0]['alt']), 33.9543253661611, places=6)
        self.assertAlmostEqual(float(result[1]['mean']), 593.551096812567, places=6)
        self.assertAlmostEqual(float(result[1]['alt']), 33.9543253661611, places=6)
        self.assertAlmostEqual(float(result[2]['mean']), 570.384204770635, places=6)
        self.assertAlmostEqual(float(result[2]['alt']), 29.9531744645919, places=6)

    def test_fatigue_safety_factor(self):
        """Regression test for fatigue_safety_factor, which calls
        variable_equivalent_stresses internally -- same just-fixed code path as
        test_variable_equivalent_stresses above, exercised end to end."""
        Fmin = [0, -6500, 0]
        Fmax = [0, -8500, 0]
        endurance_limits = self._build_endurance_limits()

        result = self.pattern.fatigue_safety_factor(endurance_limits, Fmin, Fmax)

        self.assertEqual(len(result), 3)
        # see the comment in test_variable_equivalent_stresses -- these are derived from
        # sympy Float intermediates, so compare with reduced precision.
        self.assertAlmostEqual(float(result[0]['fatigue']), 2.58404350776728, places=6)
        self.assertAlmostEqual(float(result[0]['static']), 1.03584762302638, places=6)
        self.assertAlmostEqual(float(result[1]['fatigue']), 2.58404350776728, places=6)
        self.assertAlmostEqual(float(result[1]['static']), 1.03584762302638, places=6)
        self.assertAlmostEqual(float(result[2]['fatigue']), 3.48165620415779, places=6)
        self.assertAlmostEqual(float(result[2]['static']), 1.08272451871652, places=6)

    def test_fatigue_safety_factor_verbose_does_not_raise(self):
        Fmin = [0, -6500, 0]
        Fmax = [0, -8500, 0]
        endurance_limits = self._build_endurance_limits()
        # just make sure the verbose print branch runs without error
        self.pattern.fatigue_safety_factor(endurance_limits, Fmin, Fmax, verbose=True)
