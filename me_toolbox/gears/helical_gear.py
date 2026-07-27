"""Module containing the HelicalGear class"""
# I want the variables names to be the same as in AGMA pylint: disable=invalid-name
from math import sin, cos, radians, pi, tan, atan, sqrt, degrees
import os
import numpy as np
from me_toolbox.gears import SpurGear  # for inheritance
from me_toolbox.tools import table_interpolation


class HelicalGear(SpurGear):
    """A gear object that contains all of its design parameters (AGMA 2001-D04)"""
    def __repr__(self):
        return f"{self.__class__.__name__}(m={self.modulus}, N={self.teeth_num}, " \
               f"\N{GREEK SMALL LETTER PHI}={self.pressure_angle}, " \
               f"\N{GREEK SMALL LETTER PSI}={self.helix_angle}, b={self.width})"

    def __init__(self, modulus, teeth_num, rpm, Qv, width, bearing_span, pinion_offset,
                 enclosure, hardness, pressure_angle, helix_angle, grade, work_hours=0,
                 number_of_cycles=0, crowned=False, adjusted=False, sensitive_use=False,
                 nitriding=False, case_carb=False, material='steel'):
        """Instantiating HelicalGear object which inherits from SpurGear

        :param float helix_angle: The gear helix angle (20 or 25)

        :returns: HelicalGear object
        :rtype: HelicalGear
        """
        super().__init__(modulus, teeth_num, rpm, Qv, width, bearing_span, pinion_offset,
                         enclosure, hardness, pressure_angle, grade, work_hours, number_of_cycles,
                         crowned, adjusted, sensitive_use, nitriding, case_carb, material)

        self.helix_angle = helix_angle

    @property
    def pitch_diameter(self):
        """Calculate pitch diameter

        :returns: Gear's pitch diameter
        :rtype: float
        """
        return self.teeth_num * self.tangent_modulus  # pitch diameter [mm]

    @property
    def tangent_pitch(self):
        """Calculate tangent pitch

        :returns: Gear's tangent pitch
        :rtype: float
        """

        return self.pitch / cos(radians(self.helix_angle))

    @property
    def axial_pitch(self):
        """Calculate axial pitch

        :returns: Gear's axial pitch
        :rtype: float
        """
        return self.pitch / sin(radians(self.helix_angle))

    @property
    def tangent_modulus(self):
        """Calculate tangent modulus

        :returns: Gear's tangent modulus
        :rtype: float
        """
        return self.modulus / cos(radians(self.helix_angle))

    @property
    def axial_modulus(self):
        """Calculate axial modulus

        :returns: Gear's axial modulus
        :rtype: float
        """
        return self.modulus / sin(radians(self.helix_angle))

    @property
    def tangent_pressure_angle(self):
        """Calculate tangent pressure angle

        :returns: Gear's tangent pressure angle
        :rtype: float
        """
        return degrees(atan(tan(radians(self.pressure_angle)) / cos(radians(self.helix_angle))))

    @staticmethod
    def Y_j(gear1, gear2):
        """Return Geometry factors for helical gear and pinion
        Yj is dependent on the gear ratio, helix angle and both gears teeth numbers

        :param HelicalGear gear1: Helical gear object
        :param HelicalGear gear2: Helical gear object

        :return: Yj - Geometric factor
        :rtype: float
        """

        Np = gear1.teeth_num
        Ng = gear2.teeth_num
        helix_angle = gear1.helix_angle

        # files path
        j75_path = os.path.join(os.path.dirname(__file__), "tables", "J75 - helix gear geometry factors.csv")
        jPrime_path = os.path.join(
            os.path.dirname(__file__), "tables", "JPrime - helix gear geometry factors.csv")

        # load data
        j75_data = np.genfromtxt(j75_path, delimiter=',')
        jPrime_data = np.genfromtxt(jPrime_path, delimiter=',')

        # data interpolation
        j75 = table_interpolation(Np, helix_angle, j75_data)
        jPrime = table_interpolation(Ng, helix_angle, jPrime_data)

        # calculate geometric factor Yj
        Y_j = j75 * jPrime

        gear1.Yj = Y_j
        gear2.Yj = Y_j

    @staticmethod
    def ZI(gear1, gear2):
        """Return geometric factor for contact failure
        ZI is dependent on the gear ratio, pressure angle, modulus and both gears teeth numbers

        :param HelicalGear gear1: gear object
        :param HelicalGear gear2: gear object

        :return: ZI - geometric factor
        :rtype: float
        """

        mG = gear2.teeth_num / gear1.teeth_num
        phi_t = radians(gear1.tangent_pressure_angle)
        phi_n = radians(gear1.pressure_angle)
        modulus = gear1.modulus
        tan_mod = gear1.tangent_modulus
        Np = gear1.teeth_num
        Ng = gear2.teeth_num
        z1 = sqrt((0.5 * tan_mod * Np + modulus) ** 2 - (0.5 * tan_mod * Np * cos(phi_t)) ** 2)
        z2 = sqrt((0.5 * tan_mod * Ng + modulus) ** 2 - (0.5 * tan_mod * Ng * cos(phi_t)) ** 2)
        z3 = 0.5 * tan_mod * Np * (1 + mG) * sin(phi_t)

        if z1 > z3 and z2 > z3:
            z = z3
        elif z1 > z3:
            z = z2
        elif z2 > z3:
            z = z1
        else:
            z = z1 + z2 - z3
        if gear1.width >= 2 * gear1.axial_pitch:
            mN = (gear1.pitch * cos(phi_n)) / (0.95 * z)
        else:
            raise ValueError(f"@ ZI factor: gear width should be at least two times the axial pitch"
                             f"2Px={2 * gear1.axial_pitch:.2f}")
        Z_I = (cos(phi_t) * sin(phi_t) * mG) / (2 * mN * (mG + 1))
        # print(f"ZI={Z_I}, mG={mG}, modulus={modulus}, Np={Np}, Ng={Ng}, Px={gear1.axial_pitch}")
        return Z_I

    @staticmethod
    def calc_forces(gear, power):
        """Calculate forces on helical gear

        :param HelicalGear gear: gear object
        :param float power: power

        :returns: Wt - tangent max_force, Wr - radial max_force, Wx - axial max_force in [N]
        :rtype: tuple[float, float, float]
        """

        phi_t = radians(gear.tangent_pressure_angle)
        Wt = (60e3 / pi) * (power / (gear.pitch_diameter * gear.rpm))
        Wr = Wt * tan(radians(phi_t))
        Wx = Wt * tan(radians(gear.helix_angle))
        return Wt, Wr, Wx

    def optimization(self, transmission, optimize_feature='all', verbose=False):
        """Perform gear optimization

        :param gears.transmission.Transmission transmission: Transmission object
            associated with the gear
        :param str optimize_feature: property to optimize for ('width'/'volume'/'center')
        :param bool verbose: print optimization stages

        :return: optimized result (width in mm, volume in mm^3, center distance in mm)
        :rtype: dict
        """
        gear = self

        # saving original attribute values
        original_teeth_num = gear.teeth_num  # saving original attribute
        original_width = gear.width
        original_modulus = gear.modulus

        # choosing the minimum number of teeth to start with
        initial_teeth_num = 21

        modulus_list = [0.3, 0.4, 0.5, 0.8, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 16, 20, 25]
        modulus_list.sort(reverse=True)

        results_list = []
        for modulus in modulus_list:
            # set gear modulus
            gear.modulus = modulus
            gear.teeth_num = initial_teeth_num  # updating attribute

            # because the width range is (3πm,5πm) the initial guess is 4πm
            # initial_width = 0.5 * (2 * self.axial_pitch + self.pitch_diameter)
            initial_width = gear.axial_pitch + 0.5 * gear.pitch_diameter
            gear.width = initial_width
            # print(modulus, initial_teeth_num, initial_width)
            while True:
                # update Yj factors after attribute changed
                transmission.gear1.Y_j(transmission.gear1, transmission.gear2)
                try:
                    transmission.ZI = self.ZI(transmission.gear1, transmission.gear2)
                except ValueError:
                    pass

                # KH is function of the gear width,
                # we assumed an initial width of 4πm to calculate KH,
                # we recalculate KH and the width until KH converges
                kh_not_converging = False
                while True:

                    # calculate minimum gear width for bending and contact stress
                    bending_minimum_width = transmission.minimum_width_for_bending(gear)
                    contact_minimum_width = transmission.minimum_width_for_contact(gear)
                    # print(f"bending={bending_minimum_width}, contact={contact_minimum_width}")

                    # the new width is the max value of the two minimum width
                    new_width = max(bending_minimum_width, contact_minimum_width)
                    if new_width > 1020:
                        print("error: KH is not converging for m=", self.modulus)
                        kh_not_converging = True
                        break

                    # save old KH for comparison later
                    oldKH = gear.KH

                    # save new gear width
                    gear.width = new_width

                    # update Yj factors after width changed
                    transmission.gear1.Y_j(transmission.gear1, transmission.gear2)
                    try:
                        transmission.ZI = self.ZI(transmission.gear1, transmission.gear2)
                    except ValueError:
                        pass

                    newKH = gear.KH
                    # checking convergence
                    if abs(newKH - oldKH) < 1e-6:
                        break

                # in case KH couldn't converge exit optimization for current modulus
                if kh_not_converging:
                    break

                alpha = contact_minimum_width / bending_minimum_width
                mG = transmission.gear_ratio
                centers_distance = 0.5 * gear.modulus * gear.teeth_num * (mG + 1)
                volume = 0.25 * pi * (gear.pitch_diameter ** 2) * gear.width
                f_string = f"m={gear.modulus}, N={gear.teeth_num}, b={gear.width:.2f}," \
                           f"spring_index={centers_distance:.2f}, V={volume:.2f}, α={alpha:.4f}"

                if gear.width < 2 * pi * gear.axial_pitch:
                    # gear width is less than 2Px (b<Px), gear width should be increased
                    # because the initial teeth number is minimal decrease modulus

                    modulus_list = [0.3, 0.4, 0.5, 0.8, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12,
                                    16, 20, 25]
                    # get previous modulus on the list
                    if gear.modulus > 0.3:
                        new_modulus = modulus_list[modulus_list.index(gear.modulus) - 1]
                    else:
                        raise ValueError("@ Optimize: b<2Px but the modulus is the lowest possible")

                    if verbose:
                        # printing step result
                        v = gear.tangent_velocity
                        v_max = gear.maximum_velocity
                        if not isinstance(v_max, str):
                            msg = "b<2Px" if v < v_max else "b<2Px, v>v_max"
                        else:
                            msg = "b<2Px"
                        print(f_string, ',', msg)

                    # setting changes
                    gear.modulus = new_modulus

                elif gear.width > gear.pitch_diameter:
                    # gear width is more than 5πm (b>Pd), gear width should be decreased
                    # because initial modulus is maximal increase teeth number

                    if verbose:
                        # print step result
                        v = gear.tangent_velocity
                        v_max = gear.maximum_velocity
                        if not isinstance(v_max, str):
                            msg = "b>Pd" if v < v_max else "b>Pd, v>v_max"
                        else:
                            msg = "b>Pd"
                        print(f_string, ',', msg)

                    # increasing teeth number by one
                    # (note: the gear teeth number can't exceed the biggest number specified
                    # in the Yj factor tables
                    # and for pinion a number that will make its gear pass this number.
                    # this error is handled at the Yj function)
                    gear.teeth_num += 1
                else:
                    # gear width is within range (3πm<b<5πm)
                    if alpha > 1:
                        # if α>1 increase number of teeth
                        if verbose:
                            # print step result
                            v = gear.tangent_velocity
                            v_max = gear.maximum_velocity
                            if not isinstance(v_max, str):
                                print(f"{f_string}, 2Px<b<Pd, α>1" if v < v_max
                                      else "2Px<b<Pd, α>1, v>v_max")
                            else:
                                print(f"{f_string}, 2Px<b<Pd, α>1")
                        # add result to least of viable results
                        results_list.append({'m': gear.modulus, 'N': gear.teeth_num,
                                             'b': gear.width, 'spring_index': centers_distance,
                                             'V': volume, 'alpha': alpha})
                        # increase teeth number
                        gear.teeth_num += 1
                    else:
                        # if α<=1 stop optimization and return the optimized value
                        # and a list of all viable options

                        # print optimization progress
                        if verbose:
                            # print step result
                            v = gear.tangent_velocity
                            v_max = gear.maximum_velocity
                            if not isinstance(v_max, str):
                                print(f"{f_string}, 2Px<b<Pd, α<=1" if v < v_max
                                      else "2Px<b<Pd, α<=1, v>v_max")
                            else:
                                print(f"{f_string}, 2Px<b<Pd, α<=1")

                        # find optimize feature
                        # optimize by width
                        if optimize_feature == 'width':
                            # create list of widths
                            width_list = [(dic['b'], index) for index, dic in
                                          enumerate(results_list)]
                            # get minimum width index
                            result_index = min(width_list)[1]
                            opt_res = results_list[result_index]

                        # optimize by volume
                        elif optimize_feature == 'volume':
                            # create list of volumes
                            volume_list = [(dic['V'], index) for index, dic in
                                           enumerate(results_list)]
                            # get minimum volume index
                            result_index = min(volume_list)[1]
                            opt_res = results_list[result_index]

                        # optimize by center distance
                        elif optimize_feature == 'center':
                            # create list of center distances
                            center_list = [(dic['spring_index'], index) for index, dic in
                                           enumerate(results_list)]
                            # get minimum center distance index
                            result_index = min(center_list)[1]
                            opt_res = results_list[result_index]

                        elif optimize_feature == 'all':
                            width_list = [(dic['b'], index) for index, dic in
                                          enumerate(results_list)]
                            volume_list = [(dic['V'], index) for index, dic in
                                           enumerate(results_list)]
                            center_list = [(dic['spring_index'], index) for index, dic in
                                           enumerate(results_list)]

                            opt_res = {'optimized width': results_list[min(width_list)[1]],
                                       'optimized volume': results_list[min(volume_list)[1]],
                                       'optimized center': results_list[min(center_list)[1]]}
                        else:
                            raise Exception(f"optimize_feature={optimize_feature} is invalid")

                        # restore gear parameters
                        gear.teeth_num = original_teeth_num
                        gear.width = original_width
                        gear.modulus = original_modulus

                        return opt_res, results_list

    def calc_centers_distance(self, gear_ratio):
        """ calculate the distance between the centers of the gears

        :param float gear_ratio: transmissions gear ratio

        :return: the distance between the transmissions gears centers in [mm]
        :rtype: float
        """
        centers_distance = 0.5 * self.tangent_modulus * self.teeth_num * (gear_ratio + 1)
        return centers_distance

    @staticmethod
    def create_new_gear(gear2_prop):
        """ return new instance of HelicalGear

        :param dict gear2_prop: gear properties

        :returns: HelicalGear object
        :type: HelicalGear
        """
        return HelicalGear(**gear2_prop)

    @staticmethod
    def format_properties(properties):
        """Remove excess attributes form properties

        :param list properties: list of gear properties

        :returns: A dictionary of properties
        :rtype: dict
        """
        prop_list = ['name', 'modulus', 'teeth_num', 'rpm', 'Qv', 'width', 'bearing_span',
                     'pinion_offset', 'enclosure', 'hardness', 'work_hours', 'number_of_cycles',
                     'pressure_angle', 'grade', 'crowned', 'adjusted', 'sensitive_use', 'nitriding',
                     'case_carb', 'material', 'helix_angle']
        # remove contact ratio from dictionary so it won't interfere with the new gear instantiation
        new_properties = {key: properties[key] for key in properties if key in prop_list}
        return new_properties

    def check_compatibility(self, gear):
        """Raise error if the pressure angle, helix angle or modulus of the gears don't match

        :param HelicalGear gear: gear object

        :raises ValueError("gear1 and gear2 have mismatch pressure_angle"):
        :raises ValueError("gear1 and gear2 have mismatch Helix_angle"):
        :raises ValueError("gear1 and gear2 are not the same type, they are no compatible"):
        :raises ValueError("gear1 and gear2 have mismatch modulus"):
        """

        # check pressure angles
        if self.pressure_angle != gear.pressure_angle:
            # if pressure angles are different raise error
            raise ValueError("gear1 and gear2 have mismatch pressure_angle")

        # check helix angles
        try:
            if self.helix_angle != gear.helix_angle:
                # if pressure angles are different raise error
                raise ValueError("gear1 and gear2 have mismatch Helix_angle")
        except AttributeError as err:
            raise ValueError("gear1 and gear2 are not the same type, they are no compatible") \
                from err

        # check modulus
        if self.modulus != gear.modulus:
            # if modulus are different raise error
            raise ValueError("gear1 and gear2 have mismatch modulus")
