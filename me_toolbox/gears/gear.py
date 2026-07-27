"""Module containing the Gear class"""

from math import log, sqrt, pi, tan, radians
import os
import numpy as np

from me_toolbox.tools import table_interpolation


class Gear:
    """a Gear object"""
    def __repr__(self):
        return f"{self.__class__.__name__}(m={self.modulus}, N={self.teeth_num}, " \
               f"\N{GREEK SMALL LETTER PHI}={self.pressure_angle}, b={self.width})"

    def __init__(self, modulus, teeth_num, rpm, Qv, width, bearing_span, pinion_offset,
                 enclosure, hardness, pressure_angle, grade, work_hours, number_of_cycles,
                 crowned, adjusted, sensitive_use, nitriding, case_carb, material):

        self.modulus = modulus
        self.teeth_num = teeth_num
        self.rpm = rpm
        self.Qv = Qv
        self.width = width
        self.bearing_span = bearing_span
        self.pinion_offset = pinion_offset
        self.enclosure = enclosure
        self.hardness = hardness
        self.pressure_angle = pressure_angle
        self.grade = grade
        self.crowned = crowned
        self.adjusted = adjusted
        self.sensitive_use = sensitive_use
        self.nitriding = nitriding
        self.case_carb = case_carb
        self.material = material

        if work_hours != 0:
            self.work_hours = work_hours
        if number_of_cycles != 0:
            self.number_of_cycles = number_of_cycles
        if work_hours == 0 and number_of_cycles == 0:
            raise ValueError('work_hours or number_of_cycles not specified')
        self.contact_ratio = None
        self.maximum_velocity = None

        self.Zw = None

    @property
    def pitch_diameter(self):
        """Calculate pitch diameter

        :returns: Gear's pitch diameter
        :rtype: float
        """
        return self.teeth_num * self.modulus  # pitch diameter [mm]

    @property
    def KB(self):
        """Rim thickness factor, factor_KB is dependent on the number of teeth


        :returns: Gear's Rim thickness factor
        :rtype: float
        """
        mB = (0.5 * self.teeth_num - 1.25) / 2.25
        if mB < 1.2:
            K_B = 1.6 * log(2.242 / mB)
        else:
            K_B = 1
        return K_B

    @property
    def Kv(self):
        """Dynamic factor, Kv is dependent on the pitch diameter in [mm],
        the angular velocity in [rpm] and Qv (transmission accuracy grade number)

        note: the equations here are from "Shigley's Mechanical Engineering Design"
               in the AGMA standard the transmission accuracy grade number is Av instead of Qv
               and its value is inverted, high Qv is more accurate and high Av is less accurate

        :returns: Gear's Dynamic factor
        :rtype: float
        """
        B = 0.25 * (12 - self.Qv) ** (2 / 3)
        A = 50 + 56 * (1 - B)

        # maximum velocity
        self.maximum_velocity = ((A + (self.Qv - 3)) ** 2) / 200

        if 6 <= self.Qv <= 11:
            K_v = ((A + sqrt(200 * self.tangent_velocity)) / A) ** B
        elif self.Qv == 5:
            K_v = (50 + sqrt(200 * self.tangent_velocity)) / 50
        elif self.Qv == 12:
            K_v = 1
            self.maximum_velocity = "Qv=12 no maximum velocity"
        else:
            raise ValueError(f"at Kv factor: Qv={self.Qv} not in range (5<=Qv<=12)\n")
        return K_v

    @property
    def Ks(self):
        """Size factor, factor_Ks is dependent on the circular
        pitch (p=πm) which in turn depends on the modulus

        :returns: Gear's size factor
        :rtype: float
        """
        if self.pitch > 8:
            K_s = (1 / 1.189) * (self.pitch ** 0.097)
        else:
            K_s = 1
        return K_s

    @property
    def KH(self):
        """Load distribution factor, KH is dependent on: the shape of teeth (crowned),
        if teeth are adjusted after assembly (adjusted), the gear width in [mm],
        pitch diameter in [mm], bearing span (the distance between the bearings center lines)
        pinion offset (the distance from the bearing span center to the pinion mid-face)
        enclosure type (open gearing, commercial enclosed, precision enclosed,
        extra precision enclosed)

        :returns: Gear's load distribution factor
        :rtype: float
        """
        # K_Hmc - lead correction factor
        if self.crowned:
            K_Hmc = 0.8
        else:
            K_Hmc = 1

        # K_He - mesh alignment correction factor
        if self.adjusted:
            K_He = 0.8
        else:
            K_He = 1

        # K_Hpf - mesh alignment correction factor
        # gear width to diameter ratio
        ratio = self.width / (10 * self.pitch_diameter)
        if ratio < 0.05:
            ratio = 0.05

        # print("the width is", b)
        if self.width <= 25:
            K_Hpf = ratio - 0.025
        elif 25 < self.width <= 432:
            K_Hpf = ratio - 0.0375 + 0.000492 * self.width
        elif 432 < self.width <= 1020:
            K_Hpf = ratio - 0.1109 + 0.00815 * self.width - 0.000000353 * self.width ** 2
        else:
            raise ValueError(f"at KH factor: width={self.width} not in range, (width < 1020)\n")

        # K_Hpm - pinion proportion modifier
        s = self.bearing_span
        s1 = self.pinion_offset
        if (s1 / s) < 0.175:
            K_Hpm = 1
        else:
            K_Hpm = 1.1

        # K_Hma - mash alignment factor
        enclosure_type = {'open gearing': [2.47e-1, 0.657e-3, -1.186e-7],
                          'commercial enclosed': [1.27e-1, 0.622e-3, -1.69e-7],
                          'precision enclosed': [0.675e-1, 0.504e-3, -1.44e-7],
                          'extra precision enclosed': [0.380e-1, 0.402e-3, -1.27e-7]}
        K_Hma = (enclosure_type[self.enclosure][0] + self.width * enclosure_type[self.enclosure][1]
                 + enclosure_type[self.enclosure][2] * self.width ** 2)

        K_H = 1.0 + K_Hmc * (K_Hpf * K_Hpm + K_Hma * K_He)
        return K_H

    @property
    def St(self):
        """Bending safety factor, St is dependent on the gear's
         hardness in [HBN] and the material grade
         (material grade of the gear 1 for regular use 2 for military and sensitive uses)

        :returns: Gear's bending safety factor
        :rtype: float
        """
        if self.grade == 1:
            S_t = 0.533 * self.hardness + 88.3
        elif self.grade == 2:
            S_t = 0.703 * self.hardness + 113
        else:
            raise ValueError(f"at St factor: grade={self.grade} but only 1 or 2 are valid")

        return S_t

    @property
    def Sc(self):
        """Contact safety factor, Sc is dependent on the gear
        hardness in [HBN] and on the material grade
        (material grade of the gear 1 for regular use 2 for military and sensitive uses)

        :returns: Gear's contact safety factor
        :rtype: float
        """
        if self.grade == 1:
            S_c = 200 + 2.22 * self.hardness
        elif self.grade == 2:
            S_c = 237 + 2.41 * self.hardness
        else:
            raise ValueError(f"at Sc factor: grade={self.grade} but only 1 or 2 are valid")

        return S_c

    @property
    def ZR(self):
        """For now ZR is 1 according to the AGMA standard
        :rtype: int
        """
        return 1

    @property
    def YN(self):
        """Bending strength stress cycle factor

        :returns: Gear's bending strength stress cycle factor
        :rtype: float
        """
        # get the number of cycles of the gear
        N = self.cycles_or_hours()

        if N is None:
            return None

        # 1e2 <= N < 2e6
        low_cycle = {160: 2.3194 * N ** (-0.0538),
                     'Nitrided': 3.517 * N ** (-0.0817),
                     250: 4.9404 * N ** (-0.1045),
                     'Case carb': 6.1514 * N ** (-0.1192),
                     400: 9.4518 * N ** (-0.148)}

        # N>=2e6
        high_cycle = {True: 1.6831 * N ** (-0.0323),
                      False: 1.3558 * N ** (-0.0178)}

        try:
            if 1e2 <= N < 2e6 and self.nitriding:
                curve = 'Nitrided'
            elif 1e2 <= N < 2e6 and self.case_carb:
                curve = 'Case carb'
            else:
                curve = self.hardness

            if 1e2 <= N < 2e6:
                Y_N = low_cycle[curve]
            elif N >= 2e6:
                Y_N = high_cycle[self.sensitive_use]
            else:
                raise ValueError(f" at YN: the number of cycles is {N} "
                                 f"but the minimum number is {1e2} ")
            return Y_N
        except KeyError as bad_key:
            print(f"at YN: not valid hardness {bad_key}")
            return "Error"

    @property
    def ZN(self):
        """Calculating contact strength stress cycle factor

        :returns: Gear's contact strength stress cycle
        :rtype: float
        """
        # get the number of cycles of the gear
        N = self.cycles_or_hours()
        if N is None:
            return None

        # N < 3e6
        low_cycle = {True: 1.249 * N ** (-0.0138),  # nitrided
                     False: 2.466 * N ** (-0.056)}
        # N >= 3e6
        high_cycle = {True: 2.466 * N ** (-0.056),  # for sensitive use
                      False: 1.4488 * N ** (-0.023)}

        return low_cycle[self.nitriding] if N < 3e6 else high_cycle[self.sensitive_use]

    @staticmethod
    def Y_j(gear1, gear2):
        """Return Geometry factors for spur gear and pinion

        :returns: Gear's geometry factor
        :rtype: float
        """
        N1 = gear1.teeth_num
        N2 = gear2.teeth_num
        pressure_angle = gear1.pressure_angle

        # load table according to pressure angle
        if pressure_angle == 20:
            path = os.path.join(os.path.dirname(__file__), "tables", "20deg - spur gear geometry factors.csv")
        elif pressure_angle == 25:
            path = os.path.join(os.path.dirname(__file__), "tables", "25deg - spur gear geometry factors.csv")
        else:
            raise ValueError("at spur gear Yj Factor: pressure angle is wrong")

        data = np.genfromtxt(path, delimiter=',')
        # try:
        gear1.Yj = table_interpolation(N1, N2, data)
        gear2.Yj = table_interpolation(N2, N1, data)
        # except NotInRangeError as not_in_range:
        # print(f"Error: Teeth number of one of the gears ({not_in_range.num})
        # not in range {not_in_range.range_}")

    @property
    def tangent_velocity(self):
        """Convert tangent velocity to [m/s] from [rpm]

        :returns: Gear's tangent velocity
        :rtype: float
        """
        return (pi * self.pitch_diameter * self.rpm) / 60e3

    @property
    def pitch(self):
        """Calculate circular pitch

        :returns: Gear's circular pitch
        :rtype: float
        """
        return self.modulus * pi

    def cycles_or_hours(self):
        """Check if the gear number of cycles or work hours
        were input and return the number of cycle

        :returns: Gear's Dynamic factor
        :rtype: float or None

        :raise ValueError: number of cycles and work hours entered but they're not matching
            or no number of cycles or work hours entered
        """

        if self.contact_ratio is None:
            return None

        # if attribute don't exist assign zero
        cycles_number = self.__dict__.get("number_of_cycles", 0)
        working_hours = self.__dict__.get("work_hours", 0)

        if cycles_number == 0 and working_hours != 0:
            # calculate number of cycles
            return 60 * working_hours * self.rpm * self.contact_ratio
        elif cycles_number != 0 and working_hours == 0:
            # number of cycle is an input
            return cycles_number
        elif cycles_number != 0 and working_hours != 0:
            # if both were an input check if the match
            if cycles_number == 60 * working_hours * self.rpm * self.contact_ratio:
                return cycles_number
            else:
                raise ValueError("at YN factor: number of cycles and work"
                                 "hours entered but they're not matching")
        else:
            raise ValueError("at YN factor: no number of cycles or work hours entered")

    @staticmethod
    def calc_forces(gear, power):
        """Calculate forces on the gear

        :param SpurGear gear: gear object
        :param float power: power

        :returns: Wt - tangent max_force in [N], Wr - radial max_force in [N]
        :rtype: tuple[float, float]
        """

        Wt = (60e3 / pi) * (power / (gear.pitch_diameter * gear.rpm))
        Wr = Wt * tan(radians(gear.pressure_angle))
        return Wt, Wr

    @staticmethod
    def create_new_gear(gear2_prop):
        pass

    @staticmethod
    def format_properties(properties):
        pass

    def check_compatibility(self, gear):
        pass

    @staticmethod
    def ZI(gear1, gear2):
        pass

    def calc_centers_distance(self, gear_ratio):
        pass

    def optimization(self, transmission, optimize_feature='all', verbose=False):
        pass
