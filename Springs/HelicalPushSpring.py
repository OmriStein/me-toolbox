from Springs import Spring
from math import pi, sqrt
from tools import PrintAtributes


class HelicalPushSpring(Spring):
    def __init__(self, force, wire_diameter, spring_diameter, Ap, m, shear_modulus, end_type, yield_percent,
                 zeta=0.15, spring_constant=None, set_removed=False, shot_peened=False, ends=None,
                 elastic_modulus=None, density=None, working_frequency=None):
        """
        :keyword shear_modulus: Shear modulus
        :keyword end_type: what kind of ending the spring has
        :keyword set_removed: if True adds to STATIC strength (must NOT use for fatigue application)
        :keyword shot_peened: if True adds to fatigue strength """
        super().__init__(Ap, m, yield_percent, wire_diameter, spring_diameter)

        if set_removed:
            print(f"Note: set should ONLY be removed for static loading and NOT for periodical loading")

        self.force = force
        self.set_removed = set_removed
        self.shot_peened = shot_peened
        self.shear_modulus = shear_modulus
        self.yield_percent = yield_percent
        self.spring_constant = spring_constant
        self.end_type = end_type.lower()
        self.zeta = zeta  # overrun safety factor
        end_types = ('plain', 'plain and ground', 'squared or closed', 'squared and ground')
        if self.end_type not in end_types:
            raise ValueError(f"{end_type} not one of this: {end_types}")

        self.ends = ends
        self.elastic_modulus = elastic_modulus
        self.density = density
        self.working_frequency = working_frequency

        self.CheckParam()  # check C and Na

    def getInfo(self):
        """ print all of the spring properties """
        PrintAtributes(self)
        self.CheckParam()  # check C and Na

    def CheckParam(self):
        """Check if the spring index and Na in acceptable range"""

        C = self.spring_index
        if isinstance(C, float) and not 4 <= C <= 12 and self.set_removed:
            print(f"Note: C - spring index should be in range of [4,12], lower C causes surface cracks,\n"
                  f"higher C causes the spring to tangle and requires separate packing")
        elif isinstance(C, float) and not 3 <= C <= 12:
            print(f"Note: C - spring index should be in range of [3,12], lower C causes surface cracks,\n"
                  f"higher C causes the spring to tangle and requires separate packing")

        Na = self.Na
        if isinstance(Na, float) and not 3 <= Na <= 15:
            print(f"Note: Na={Na:.2f} is not in range [3,15], this can cause non linear behavior")

        zeta = self.zeta
        if zeta < 0.15:
            print(f"Note: zeta={zeta:.2f} is smaller then 0.15, the spring could reach its solid length")

        L0 = self.free_length
        if isinstance(L0, float) and (self.ends is not None) and (self.elastic_modulus is not None):
            buckling = self.Buckling(self.ends, self.elastic_modulus)
            if buckling[0]:
                print(f"Note: buckling is accruing , max free length (L0) = {buckling[1]} , L0= {L0}")
        if (self.density is not None) and (self.working_frequency is not None):
            Wn = self.NaturalFrequency(self.density)
            if Wn <= 20 * self.working_frequency:
                print(
                    f"Note: the natural frequency={Wn} is less than 20*working frequency={20 * self.working_frequency}")

    @property
    def spring_index(self):
        """ C - spring index

            Note: C should be in range of [4,12], lower C causes surface cracks,
                higher C causes the spring to tangle and require separate packing """
        return self.spring_diameter / self.wire_diameter

    # TODO: change Na to active_coils
    @property
    def Na(self):
        """ Calculate Na which is the number of active coils (using Castigliano's theorem) """
        return ((self.shear_modulus * self.wire_diameter) / (8 * self.spring_index ** 3 * self.spring_constant)) * (
                (2 * self.spring_index ** 2) / (1 + 2 * self.spring_index ** 2))

    @property
    def Ks(self):
        """ Ks - Static Shear stress concentration factor """
        return (2 * self.spring_index + 1) / (2 * self.spring_index)

    @property
    def Kw(self):
        """ K_W - Wahl shear stress concentration factor """
        return (4 * self.spring_index - 1) / (4 * self.spring_index - 4) + (0.615 / self.spring_index)

    @property
    def KB(self):  # NOT IMPLEMENTED!!! TODO: check when to use and implement
        """ K_B - Bergstrasser shear stress concentration factor (very close to Kw)"""
        return (4 * self.spring_index + 2) / (4 * self.spring_index - 3)

    @property
    def max_shear_stress(self):
        """ maximum shear stress """
        return self.CalcShearStress(self.force)

    def CalcShearStress(self, force):
        K = self.Ks if self.set_removed else self.Kw
        return (K * 8 * force * self.spring_diameter) / (pi * self.wire_diameter ** 3)

    @property
    def deflection(self):
        """ spring deflection (change in length) """
        return ((8 * self.force * self.spring_index ** 3 * self.Na) / (self.shear_modulus * self.wire_diameter)) * (
                (1 + 2 * self.spring_index ** 2) / (2 * self.spring_index ** 2))

    @property
    def end_coils(self):
        """ Ne - the end coils of the spring"""
        options = {'plain': 0, 'plain and ground': 1, 'squared or closed': 2, 'squared and ground': 2}
        return options.get(self.end_type)

    @property
    def total_coils(self):
        """ Nt - the total coils of the spring"""
        return self.end_coils + self.Na

    @property
    def solid_length(self):
        """ Ls - the solid length of the spring
            (if the spring is fully compressed so the coils are touching each other) """

        d = self.wire_diameter
        Nt = self.total_coils
        options = {'plain': d * (Nt + 1), 'plain and ground': d * Nt, 'squared or closed': d * (Nt + 1),
                   'squared and ground': d * Nt}
        return options.get(self.end_type)

    @property
    def Fsolid(self):
        # it is a good practice for the force that compresses the spring to solid state to be: Fs=(1+zeta)Fmax
        # where zeta is the overrun safety factor, it's customary that zeta=0.15 so Fs=1.15Fmax
        return (1 + self.zeta) * self.force

    @property
    def free_length(self):
        return (self.Fsolid / self.spring_constant) + self.solid_length

    @property
    def static_safety_factor(self):
        return self.Ssy / self.max_shear_stress

    def weight(self, density):
        """ return the spring weight according to the specified density """
        return 0.25 * density * (pi ** 2) * (self.wire_diameter ** 2) * self.spring_diameter * self.Na

    def CalcSpringConstant(self, Na):
        """ Calculate the spring constant if Na is Known (using Castigliano's theorem) """
        return ((self.shear_modulus * self.wire_diameter) / (8 * self.spring_index ** 3 * Na)) * (
                (2 * self.spring_index ** 2) / (1 + 2 * self.spring_index ** 2))

    def MinWireDiameter(self, safety_factor, solid=False):
        """ The minimal wire diameter for a given safety factor in order to avoid failure,
            according to the spring parameters """
        K = self.Ks if self.set_removed else self.Kw
        force = self.Fsolid if solid else self.force
        return ((8 * K * force * self.spring_index * safety_factor) / (
                self.yield_percent * self.Ap * pi)) ** (1 / (2 - self.m))

    # TODO: test MaxForce implementation
    def MaxForce(self, safety_factor):
        """ The maximum force for a given safety factor in order to avoid failure,
            according to the spring parameters. """
        K = self.Ks if self.set_removed else self.Kw
        force = ((self.yield_percent * self.Ap * pi * self.wire_diameter ** (2 - self.m)) / (
                8 * K * self.spring_index * safety_factor))
        if force > self.Fsolid:
            print("Fsolid exceeded")
            return self.Fsolid / (1 + self.zeta)
        else:
            return force

    def Buckling(self, ends, E):
        """ Absolute stability

        :keyword E: elastic modulus
        :type E: float
        :keyword ends: the spring end condition (from Table 10-2)
        :type ends: str
        :returns: returns True if spring is in danger of collapse and False if not
            and the maximum free length(L0) before collapsing """

        alpha = {'fixed-fixed': 0.5, 'fixed-hinged': 0.707, 'hinged-hinged': 1, 'clamped-free': 2}  # from table 10-2

        L0 = self.free_length
        try:
            collapse_test = (pi * self.spring_diameter / alpha[ends.lower()]) * sqrt(
                (2 * (E - self.shear_modulus)) / (2 * self.shear_modulus + E))
        except ValueError as e:
            print(f"{e}, make sure E and G have the same units (Mpa)")
        except KeyError as key:
            print(f"Ends: {key} is unknown ")
        else:
            return L0 >= collapse_test, collapse_test

    def Sse(self, reliability):
        """ Shear endurance limit according to Zimmerli

            :returns: Ke - reliability factor
            :rtype: float """

        import numpy as np
        percentage = np.array([50, 90, 95, 99, 99.9, 99.99, 99.999, 99.9999])
        reliability_factors = np.array([1, 0.897, 0.868, 0.814, 0.753, 0.702, 0.659, 0.620])
        Ke = np.interp(reliability, percentage, reliability_factors)

        if self.shot_peened:
            Ssa, Ssm = 398, 534
        else:
            Ssa, Ssm = 241, 379

        return Ke * (Ssa / (1 - (Ssm / self.Ssu) ** 2))

    def FatigueAnalysis(self, Fmax, Fmin, reliability):
        # calculating mean and alternating forces
        alternating_force = abs(Fmax - Fmin) / 2
        mean_force = (Fmax + Fmin) / 2

        # calculating mean and alternating stresses
        alternating_shear_stress = self.CalcShearStress(alternating_force)
        mean_shear_stress = self.CalcShearStress(mean_force)

        # nf - goodman fatigue safety factor
        nf = 1 / ((alternating_shear_stress / self.Sse(reliability)) + (mean_shear_stress / self.Ssu))
        # ns - langer safety factor for first cycle
        ns = self.Ssy / (mean_shear_stress + alternating_shear_stress)

        return nf, ns

    def NaturalFrequency(self, density):
        return (self.wire_diameter / (2 * self.spring_diameter ** 2 * self.Na * pi)) * sqrt(
            self.shear_modulus / (2 * density))
