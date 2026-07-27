"""A module containing the spring class"""
import csv
import os
import numpy as np

from me_toolbox.tools import print_atributes
from me_toolbox.tools import percent_to_decimal
from abc import ABC, abstractmethod

class Spring(ABC):

    def __repr__(self):
        return f"Spring(max_force={self.max_force}, wire_diameter={self.wire_diameter}, " \
               f"diameter={self.diameter}, spring_rate={self.spring_rate}, " \
               f"active_coils={self.active_coils}, " \
               f"ultimate_tensile_strength={self.ultimate_tensile_strength}, " \
               f"shear_modulus={self.shear_modulus}, elastic_modulus={self.elastic_modulus}," \
               f"shot_peened={self.shot_peened}, density={self.density})"

    def __str__(self):
        return f"{self.__class__.__name__}(K={self.spring_constant}, d={self.wire_diameter}, " \
               f"D={self.diameter})"

    def __init__(self, max_force, wire_diameter, diameter, spring_rate,
                 ultimate_tensile_strength, shear_modulus, elastic_modulus, shot_peened,
                 density):
        """Instantiate helical push spring object with the given parameters
        :param float max_force: The maximum load on the spring [N]
        :param float wire_diameter: Spring wire diameter [mm]
        :param float diameter: Spring diameter measured from [mm]
            the center point of the wire diameter
        :param float or None spring_rate: Spring rate (k) [N/mm]
        :param float ultimate_tensile_strength: Ultimate tensile strength of the material [MPa]
        :param float shear_modulus: Shear modulus [MPa]
        :param float or None elastic_modulus: Elastic modulus (used for buckling calculations) [MPa]
        :param bool shot_peened: If True adds to fatigue strength
        :param float or None density: Spring's material density [kg/m^3]

        :returns: Spring object
        """

        self.max_force = max_force
        self.wire_diameter = wire_diameter
        self.diameter = diameter
        self.spring_rate = spring_rate
        self.ultimate_tensile_strength = ultimate_tensile_strength
        self.shear_modulus = shear_modulus
        self.elastic_modulus = elastic_modulus
        self.density = density
        self.shot_peened = shot_peened

    def get_info(self):
        """print all the spring properties"""
        print_atributes(self)

    @property
    def wire_diameter(self):
        """Getter for the wire diameter attribute

        :returns: The spring's wire diameter
        :rtype: float
        """
        return self._wire_diameter

    @wire_diameter.setter
    def wire_diameter(self, diameter):
        """Sets the wire diameter and updates relevant attributes
        :param float diameter: Spring's wire diameter
        """
        self._wire_diameter = diameter

    @property
    def diameter(self):
        """Getter for the spring diameter attribute

        :returns: The spring diameter
        :rtype: float
        """
        return self._diameter

    @diameter.setter
    def diameter(self, diameter):
        """Sets the spring diameter and updates relevant attributes
        :param float diameter: Spring's diameter
        """
        self._diameter = diameter

    @property
    def inside_diameter(self):
        return self.diameter - self.wire_diameter

    @property
    def outside_diameter(self):
        return self.diameter + self.wire_diameter

    @property
    def spring_index(self):
        """C - spring index

        Note: C should be in range of [4,12], lower C causes surface cracks,
            higher C causes the spring to tangle and require separate packing

        :returns: The spring index
        :type: float
        """
        return self.diameter / self.wire_diameter

    @property
    def spring_rate(self):
        """getter for the :attr:`spring_rate` attribute

        :returns: The spring rate
        :rtype: float
        """
        return self._spring_rate

    @spring_rate.setter
    def spring_rate(self, spring_rate):
        """setter for the :attr:`spring_rate` attribute
        :param float or None spring_rate: K - The spring rate
        """
        self._spring_rate = spring_rate

    @property
    def shear_ultimate_strength(self):
        """ Ssu - ultimate tensile strength for shear """
        return 0.67 * self.ultimate_tensile_strength

    def shear_endurance_limit(self, reliability=50, metric=True):
        """Sse - Shear endurance limit according to Zimmerli
        :param float reliability: reliability in percentage
        :param bool metric: metric or imperial

        :returns: Sse - Shear endurance limit
        :rtype: float
        """
        # data from table
        percentage = np.array([50, 90, 95, 99, 99.9, 99.99, 99.999, 99.9999])
        reliability_factors = np.array([1, 0.897, 0.868, 0.814, 0.753, 0.702, 0.659, 0.620])
        # interpolating from data
        Ke = np.interp(reliability, percentage, reliability_factors)

        if self.shot_peened:
            Ssa, Ssm = (398, 534) if metric else (57.5e3, 77.5e3)
        else:
            Ssa, Ssm = (241, 379) if metric else (35e3, 55e3)

        return Ke * (Ssa / (1 - (Ssm / self.shear_ultimate_strength) ** 2))

    def endurance_limit(self, percent, reliability=50):
        """Endurance limit (Se) according to the repeated bending stress
        :param float percent: Percent of Tensile Strength
        :param float reliability: reliability in percentage

        :returns: Endurance limit (Se)
        :rtype: float
        """
        # data from table
        percentage = np.array([50, 90, 95, 99, 99.9, 99.99, 99.999, 99.9999])
        reliability_factors = np.array([1, 0.897, 0.868, 0.814, 0.753, 0.702, 0.659, 0.620])
        # interpolating from data
        Ke = np.interp(reliability, percentage, reliability_factors)

        Sut = self.ultimate_tensile_strength

        try:
            return percent_to_decimal(percent) * Sut
        except TypeError:
            Sr = percent * Sut

        return Ke * (0.5 * Sr) / (1 - (0.5*Sr/Sut)**2)

    @staticmethod
    def material_prop(material, diameter, metric=True, verbose=False):
        """Reads table A_and_m.csv from file and returns the Sut estimation from the material
         properties Ap and m
        :param str material: The spring's material
        :param float diameter: Wire diameter
        :param bool metric: Metric or imperial
        :param bool verbose: Prints Values of A and m

        :returns: ultimate tensile strength (Sut)
        :rtype: float
        """

        path = os.path.join(os.path.dirname(__file__), "tables", "ultimate _tensile_strength.csv")
        with open(path, newline='') as file:
            reader = csv.DictReader(file)
            table = []
            available_types = []
            for line in reader:
                table.append(line)
                available_types.append(line['type'])

        for line in table:
            min_d = float(line['min_d_mm'] if metric else line['min_d_in'])
            max_d = float(line['max_d_mm'] if metric else line['max_d_in'])
            if line['type'] == material.lower() and min_d <= diameter <= max_d:
                A, m = float(line['A_mm'] if metric else line['A_in']), float(line['m'])
                if verbose:
                    print(f"A={A}, m={m}")
                return A / (diameter ** m)

        if material not in available_types:
            raise KeyError("The material is unknown")
        else:
            raise ValueError("The diameter don't match any of the values in the table")

    @abstractmethod
    def static_analysis(self):
        pass

    @abstractmethod
    def fatigue_analysis(self):
        pass
