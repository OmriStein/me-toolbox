"""module containing the BoltPattern class used for a bolt pattern strength analysis"""
from numpy import array, cross, dot, sqrt
from numpy.linalg import norm

from me_toolbox.fatigue import FatigueAnalysis, EnduranceLimit
from me_toolbox.tools import print_atributes


class BoltPattern:
    def __repr__(self):
        return f"BoltPattern(fasteners={[str(fastener) for fastener in self.fasteners]}, " \
               f"fasteners_locations={self.fasteners_locations}, " \
               f"force={self.force}, force_location={self.force_location}, " \
               f"axis_of_rotation={self.axis_of_rotation}, shear_location={self.shear_location})"

    def __str__(self):
        return f"Pattern({[str(fastener) for fastener in self.fasteners]})"

    def __init__(self, fasteners, fasteners_locations, force, force_location,
                 axis_of_rotation, shear_location):
        """Initialize bolt pattern
        :param list[ThreadedFastener] fasteners: A List of threaded fasteners object
        e.g. [M10_fastener, M10_fastener, M8_fastener, M8_fastener]
        :param list[list] fasteners_locations: A list of coordinates for each of the
         fasteners locations
        :param list force: The external force in vector form [x,y,z]
        :param list force_location: The external force location in vector form [x,y,z]
        :param list[list] axis_of_rotation: List of two points that describe the axis of
        rotation
        :param string shear_location: Where along the volt the shear is felt, shank or thread
        used to determine what area value to use
        """

        self.fasteners = fasteners
        self.fasteners_locations = fasteners_locations
        self.force = force
        self.preloads = [load.preload for load in self.fasteners]
        self.force_location = force_location
        self.axis_of_rotation = axis_of_rotation
        self.shear_location = shear_location

    def get_info(self):
        """print all the fastener properties"""
        print_atributes(self)

    @property
    def fasteners_stiffness(self):
        """bolts' fastener stiffness (C)"""
        return [fastener.fastener_stiffness for fastener in self.fasteners]

    @property
    def total_stiffness(self):
        """fasteners' total stiffness list (Kb+Km)"""
        return [fastener.member_stiffness + fastener.bolt_stiffness for fastener in self.fasteners]

    @property
    def bolt_shear_area(self):
        """if the shear stress is in the threaded section the shear area is the stress areas
           if the shear stress is in the shank section the shear area is the shank area"""
        if self.shear_location == 'shank':
            return [fastener.bolt.nominal_area for fastener in self.fasteners]
        elif self.shear_location == 'thread':
            return [fastener.bolt.stress_area for fastener in self.fasteners]
        else:
            raise ValueError("shear_location can be 'shank' or 'thread'")

    @property
    def shear_stress(self):
        """bolts' shear stress"""
        return [norm(i) / j for i, j in zip(self.total_shear_force, self.bolt_shear_area)]

    @property
    def total_shear_force(self):
        """the total shear force on bolt from the direct shear force and resulting torque
        (Fi = Fvi+FGi)"""
        return [i + j for i, j in zip(self.direct_shear_force, self.torque_shear_force)]

    @property
    def direct_shear_force(self):
        """shear forces directly from the external force (Fvi)"""
        force = array(self.force)

        # zeroing forces in the z direction (because they don't cause shear)
        force[2] = 0

        return [(force * area) / sum(self.bolt_shear_area) for area in self.bolt_shear_area]

    @property
    def center_of_rotation(self):
        """center of rotation for an off center shear force"""
        bolts_x_locations = [bolt[0] for bolt in self.fasteners_locations]
        bolts_y_locations = [bolt[1] for bolt in self.fasteners_locations]
        bolts_z_locations = [bolt[2] for bolt in self.fasteners_locations]
        # calculating center of rotation (G)
        Gx, Gy, Gz = 0, 0, 0
        for area, location in zip(self.bolt_shear_area, bolts_x_locations):
            Gx += (area * location) / sum(self.bolt_shear_area)
        for area, location in zip(self.bolt_shear_area, bolts_y_locations):
            Gy += (area * location) / sum(self.bolt_shear_area)
        for area, location in zip(self.bolt_shear_area, bolts_z_locations):
            Gz += (area * location) / sum(self.bolt_shear_area)
        return Gx, Gy, Gz

    @property
    def torque_shear_force(self):
        """shear forces from the resulting torque (FGi)"""

        center_of_rotation = array(self.center_of_rotation)
        force_relative_to_G = array(self.force_location) - center_of_rotation
        torque_around_G = cross(force_relative_to_G, array(self.force))

        # zeroing torques not in the z direction (because they don't cause shear)
        torque_around_G[0] = 0
        torque_around_G[1] = 0

        rGi = [array(i) - center_of_rotation for i in self.fasteners_locations]

        force_times_area = [cross(torque_around_G, rGi[i]) * j for i, j in
                            enumerate(self.bolt_shear_area)]
        b = 0
        for i, j in enumerate(self.bolt_shear_area):
            b += j * norm(rGi[i]) ** 2

        return [a / b for a in force_times_area]

    @property
    def normal_stress(self):
        """normal stress in the bolt"""
        bolt_stress_area = [fastener.bolt.stress_area for fastener in self.fasteners]
        return self.bolt_load / bolt_stress_area

    @property
    def bolt_load(self):
        """tension force in the bolt (Fbj)"""
        return array(self.preloads) + (array(self.fastener_load) * array(self.fasteners_stiffness))

    @property
    def fastener_load(self):
        """the total normal force on bolt from the direct force and resulting bending moment (Pj)"""
        return [abs(i[2] + j[2]) for i, j in zip(self.direct_normal_load, self.bending_normal_load)]

    @property
    def direct_normal_load(self):
        """normal force directly from pure tension (PTj)"""
        normal_force = self.force[2]
        return [array([0, 0, (normal_force * stiffness) / sum(self.total_stiffness)]) for stiffness
                in self.total_stiffness]

    @property
    def neutral_point(self):
        """The location of the neutral point of tension"""
        bolts_x_locations = [bolt[0] for bolt in self.fasteners_locations]
        bolts_y_locations = [bolt[1] for bolt in self.fasteners_locations]
        bolts_z_locations = [bolt[2] for bolt in self.fasteners_locations]

        # location of the neutral point of tension
        Hx, Hy, Hz = 0, 0, 0
        for stiffness, location in zip(self.total_stiffness, bolts_x_locations):
            Hx += (stiffness * location) / sum(self.total_stiffness)
        for stiffness, location in zip(self.total_stiffness, bolts_y_locations):
            Hy += (stiffness * location) / sum(self.total_stiffness)
        for stiffness, location in zip(self.total_stiffness, bolts_z_locations):
            Hz += (stiffness * location) / sum(self.total_stiffness)
        return Hx, Hy, Hz

    @property
    def bending_normal_load(self):
        """normal force resulting from the bending moment (PMTVj)"""
        Hx, Hy, Hz = self.neutral_point

        # finding resulting moment relative to neutral center
        neutral_center = array([Hx, Hy, 0])
        force_relative_to_H = array(self.force_location) - neutral_center
        moment_around_H = cross(force_relative_to_H, array(self.force))
        # zeroing moment in the z direction (because it doesn't cause tension)
        moment_around_H[2] = 0

        # finding bolts distances from rotation edge
        edge_p1, edge_p2 = array(self.axis_of_rotation)
        edge_vector = edge_p2 - edge_p1
        perpendicular_edge_vector = [-edge_vector[1], edge_vector[0]]
        edge_direction = perpendicular_edge_vector / norm(perpendicular_edge_vector)
        distance_from_edge = [cross(edge_vector, p0[:-1] - edge_p1) / norm(edge_vector) *
                              edge_direction for p0 in array(self.fasteners_locations)]

        # edge = array(self.axis_of_rotation)
        # edge_direction = edge / norm(edge)
        # distance_from_edge = [edge + dot(r, edge_direction) * edge_direction for r in
        #                             array(self.fasteners_locations)]

        force_times_stiffness = [cross(moment_around_H, distance_from_edge[i]) * j for i, j in
                                 enumerate(self.total_stiffness)]

        b = 0
        for i, j in enumerate(self.total_stiffness):
            b += j * norm(distance_from_edge[i]) ** 2
        return [a / b for a in force_times_stiffness]

    @property
    def equivalent_stresses(self):
        """equivalent stresses according to Von-mises"""
        return [sqrt(normal_stress ** 2 + 3 * shear_stress ** 2) for normal_stress, shear_stress in
                zip(self.normal_stress, self.shear_stress)]

    def load_safety_factor(self, minimal_value=True, verbose=False):
        """Safety factor for loading (nL)
                :param bool minimal_value: If true returns the lowest safety factor of all the
                fasteners, if false returns a list of safety factors for each of the fasteners
                :param bool verbose: If true prints the safety value for each fastener
        """
        proof_loads = array([fastener.bolt.proof_load for fastener in self.fasteners])
        nL = (proof_loads - array(self.preloads)) / (self.bolt_load - array(self.preloads))
        if verbose:
            for i, fastener in enumerate(self.fasteners):
                print(f"{fastener} - nL = {nL[i]:.2f}")
            print("")
        return min(nL) if minimal_value else nL

    def separation_safety_factor(self, minimal_value=True, verbose=False):
        """Safety factor against fastener separation (n0)
                :param bool minimal_value: If true returns the lowest safety factor of all the
                fasteners, if false returns a list of safety factors for each of the fasteners
                :param bool verbose: If true prints the safety value for each fastener
        """
        n0 = array(self.preloads) / ((1 - array(self.fasteners_stiffness)) * self.fastener_load)
        if verbose:
            for i, fastener in enumerate(self.fasteners):
                print(f"{fastener} - n0 = {n0[i]:.2f}")
            print("")
        return min(n0) if minimal_value else n0

    def proof_safety_factor(self, minimal_value=True, verbose=False):
        """Safety factor for proof strength (np)
                :param bool minimal_value: If true returns the lowest safety factor of all the
                fasteners, if false returns a list of safety factors for each of the fasteners
                :param bool verbose: If true prints the safety value for each fastener
        """
        np = [fastener.bolt.proof_strength / eq for fastener, eq in
              zip(self.fasteners, self.equivalent_stresses)]
        if verbose:
            for i, fastener in enumerate(self.fasteners):
                print(f"{fastener} - np = {np[i]:.2f}")
            print("")
        return min(np) if minimal_value else np

    def variable_loading_stresses(self, Fmin, Fmax):
        """
        Returns the alternating and mean normal and shear stresses
            :param list[float] Fmin: Minimum force
            :param list[float] Fmax: Maximum force
            :return:A List of the alternating normal stress, a List of the alternating shear stress,
            a List of the mean normal stress and a List of the mean shear stress
            :rtype: dict{'alt_normal_stress': float,
                         'alt_shear_stress': float,
                         'mean_normal_stress': float,
                         'mean_shear_stress': float}
        """
        force = self.force  # saving the original force used in the class call

        # setting the pattern force attribute as the minimum force and
        # retrieving the minimum normal stress and the minimum shear stress
        # from the updated class properties
        self.force = Fmin
        min_normal_stress = array(self.normal_stress)
        min_shear_stress = array(self.shear_stress)

        # setting the pattern force attribute as the maximum force and
        # retrieving the maximum normal stress and the maximum shear stress
        # from the updated class properties
        self.force = Fmax
        max_normal_stress = array(self.normal_stress)
        max_shear_stress = array(self.shear_stress)

        alt_normal_stress = (max_normal_stress - min_normal_stress) / 2
        alt_shear_stress = (max_shear_stress - min_shear_stress) / 2
        mean_normal_stress = (max_normal_stress + min_normal_stress) / 2
        mean_shear_stress = (max_shear_stress + min_shear_stress) / 2

        self.force = force  # restoring the original force used in the class call

        return {'alt_normal_stress': alt_normal_stress,
                'alt_shear_stress': alt_shear_stress,
                'mean_normal_stress': mean_normal_stress,
                'mean_shear_stress': mean_shear_stress}

    def variable_equivalent_stresses(self, endurance_limit, Fmin, Fmax):
        """Returns the mean and alternating equivalent stress (σ_eq_a and σ_eq_m)
            :param list[EnduranceLimit] endurance_limit: List of the pattern's bolts
            endurance limit objects
            :param list[float] Fmin: Minimum force
            :param list[float] Fmax: Maximum force

            :returns: list of mean and alternating equivalent stresses pairs for each of the
            pattern's bolts
            :rtype: list[dict{'mean': float, 'alt': float}]
        """
        alt_normal_stress, alt_shear_stress, mean_normal_stress, mean_shear_stress = \
            self.variable_loading_stresses(Fmin, Fmax).values()
        variable_eq_stresses = []
        for i, fastener in enumerate(self.fasteners):
            analysis = FatigueAnalysis(modified_endurance_limit=endurance_limit[i].modified,
                                       stress_type='multiple', ductile=True,
                                       ultimate_tensile_strength=fastener.bolt.tensile_strength,
                                       yield_strength=fastener.bolt.yield_strength,
                                       Kf_normal=fastener.bolt.Kf,
                                       Kf_torsion=fastener.bolt.Kf,
                                       alt_normal_stress=alt_normal_stress[i],
                                       alt_torsion_stress=alt_shear_stress[i],
                                       mean_normal_stress=mean_normal_stress[i],
                                       mean_torsion_stress=mean_shear_stress[i])
            variable_eq_stresses.append({'mean': analysis.mean_eq_stress,
                                         'alt': analysis.alt_eq_stress})
        return variable_eq_stresses

    def fatigue_safety_factor(self, endurance_limits, Fmin, Fmax, verbose=False):
        """
        Returns the fatigue(Goodman) and static(Langar) safety factors for each bolt
        :param list[EnduranceLimit] endurance_limits: the EnduranceLimit object of each bolt
        :param list[float] Fmin: Minimum force
        :param list[float] Fmax: Maximum force
        :param bool verbose: Print additional information
        :return: A list of the fatigue and static safety factors pairs for each of the bolts
        :rtype: list[dict{'fatigue': float, 'static': float}]
        """
        variable_eq_stress = self.variable_equivalent_stresses(endurance_limits, Fmin, Fmax)

        safety_factors = []
        for i, fastener in enumerate(self.fasteners):
            preload_stress = fastener.preload / fastener.bolt.stress_area
            mean_stress = variable_eq_stress[i]['mean']
            alt_stress = variable_eq_stress[i]['alt']
            Sut = fastener.bolt.tensile_strength
            Se = endurance_limits[i].modified
            Sp = fastener.bolt.proof_strength
            if verbose:
                print(f"σi={preload_stress}, σa={alt_stress}, σm={mean_stress}, Sut={Sut}, Se={Se}")
            nf = ((Se * (Sut - preload_stress)) /
                  (Sut * alt_stress + Se * (mean_stress - preload_stress)))
            ns = Sp / (mean_stress + alt_stress)
            safety_factors.append({'fatigue': nf, 'static': ns})
        return safety_factors
