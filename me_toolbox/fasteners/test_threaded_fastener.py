from unittest import TestCase
from math import log, pi, tan, radians
import numpy as np

from me_toolbox.fasteners import Bolt
from me_toolbox.fasteners import ThreadedFastener


def stiffness(d, Diam, thickness, Elastic):
    stiff = []
    for D, t, E in zip(Diam, thickness, Elastic):
        ln = log(((1.155 * t + D - d) * (D + d)) / ((1.155 * t + D + d) * (D - d)))
        stiff.append(0.5774 * pi * E * d / ln)
    km_inv = sum(1 / np.array(stiff))
    return 1 / km_inv


class TestThreadedFastener(TestCase):
    tan_alpha = tan(radians(30))

    def setUp(self):
        diameter = 10
        pitch = 1.5
        length = 20
        threaded_length = 15
        grade = '12.9'
        E = 207e3

        Sp, Sut, Sy = Bolt.get_strength_prop(diameter, grade)

        self.bolt = Bolt(diameter, pitch, length, threaded_length, Sy, Sut, Sp, E)

        thickness = [2, 3, 3, 2, 3]
        Elastic = [200e3, 70e3, 200e3, 200e3, 200e3]
        self.layers = [[t, E] for t, E in zip(thickness, Elastic)]
        self.grip_len = (sum([layer[0] for layer in self.layers]))
        self.fastener = ThreadedFastener(self.bolt, self.layers, nut=True)

    def test_griped_thread(self):
        self.assertAlmostEqual(self.fastener.griped_thread_length, 8)

    def test_bolt_stiffness(self):
        self.assertAlmostEqual(self.fastener.bolt_stiffness, 1026695.2877576174)

    def test_member_stiffness_1(self):
        # test if the first substrate is smaller than half the material
        thickness = [2, 3, 3, 2, 3]
        Elastic = [200e3, 70e3, 200e3, 200e3, 200e3]
        layers = [(t, E) for t, E in zip(thickness, Elastic)]

        D1, D6 = 15, 15
        D2 = D1 + 2 * thickness[0] * self.tan_alpha
        D3 = D2 + 2 * thickness[1] * self.tan_alpha
        D5 = D6 + 2 * thickness[2] * self.tan_alpha
        D4 = D5 + 2 * thickness[3] * self.tan_alpha
        Diam = [D1, D2, D3, D4, D5, D6]
        km = stiffness(self.bolt.diameter, Diam, [2, 3, 1.5, 1.5, 2, 3],
                       [200e3, 70e3, 200e3, 200e3, 200e3, 200e3])
        self.fastener.layers = layers
        self.assertAlmostEqual(self.fastener.member_stiffness, km)

    def test_member_stiffness_2(self):
        # test if the first substrate is smaller than half the material
        thickness = [2, 4, 4]
        Elastic = [200e3, 70e3, 200e3]
        layers = [(t, E) for t, E in zip(thickness, Elastic)]
        D1, D4 = 15, 15
        D2 = D1 + 2 * thickness[0] * self.tan_alpha
        D3 = D4 + 2 * thickness[2] * self.tan_alpha
        Diam = [D1, D2, D3, D4]

        km = stiffness(self.bolt.diameter, Diam, [2, 3, 1, 4], [200e3, 70e3, 70e3, 200e3])
        self.fastener.layers = layers
        self.assertAlmostEqual(self.fastener.member_stiffness, km)

    def test_member_stiffness_3(self):
        # test if the first substrate is larger than half the material
        thickness = [5, 1, 2]
        Elastic = [200e3, 70e3, 200e3]
        layers = [(t, E) for t, E in zip(thickness, Elastic)]
        D1, D4 = 15, 15
        D3 = D4 + 2 * thickness[2] * self.tan_alpha
        D2 = D3 + 2 * thickness[1] * self.tan_alpha
        Diam = [D1, D2, D3, D4]
        km = stiffness(self.bolt.diameter, Diam, [4, 1, 1, 2], [200e3, 200e3, 70e3, 200e3])
        self.fastener.layers = layers
        self.assertAlmostEqual(self.fastener.member_stiffness, km)

    def test_member_stiffness_4(self):
        # test symmetric layers
        thickness = [2, 4, 2]
        Elastic = [200e3, 70e3, 200e3]
        layers = [(t, E) for t, E in zip(thickness, Elastic)]
        D1, D4 = 15, 15
        D2 = D1 + 2 * thickness[0] * self.tan_alpha
        D3 = D4 + 2 * thickness[2] * self.tan_alpha
        Diam = [D1, D2, D3, D4]
        km = stiffness(self.bolt.diameter, Diam, [2, 2, 2, 2], [200e3, 70e3, 70e3, 200e3])
        self.fastener.layers = layers
        self.assertAlmostEqual(self.fastener.member_stiffness, km)

    def test_member_stiffness_5(self):
        # test center between layers
        thickness = [2, 3, 3, 2]
        Elastic = [200e3, 70e3, 200e3, 200e3]
        layers = [(t, E) for t, E in zip(thickness, Elastic)]
        D1, D4 = 15, 15
        D2 = D1 + 2 * 2 * self.tan_alpha
        D3 = D4 + 2 * 2 * self.tan_alpha
        Diam = [D1, D2, D3, D4]
        km = stiffness(self.bolt.diameter, Diam, thickness, Elastic)
        self.fastener.layers = layers
        self.assertAlmostEqual(self.fastener.member_stiffness, km)

    def test_fastener_stiffness(self):
        self.assertAlmostEqual(self.fastener.fastener_stiffness, 0.33840496783181806)
