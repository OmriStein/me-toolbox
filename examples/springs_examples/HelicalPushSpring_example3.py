from me_toolbox.springs import HelicalPushSpring
from sympy import symbols, Eq, solveset

outer_diameter = 14.29
d = 2.337
D = outer_diameter - d
L0 = 111.12

# Chrome-vanadium wire
G, E, Ap, m, yield_percent = 77.2e3, 203.4, 2005, 0.168, 0.45

K = symbols('K')
Fmax = 105.7  # [N]
Fmin = 12.24  # [N]
spring = HelicalPushSpring(max_force=Fmax, wire_diameter=d, spring_diameter=D,
                           shear_yield_percent=yield_percent, end_type='squared and ground',
                           shear_modulus=G, elastic_modulus=E, Ap=Ap, m=m, spring_constant=None,
                           active_coils=21, free_length=L0, set_removed=False, shot_peened=False)

nf, ns = spring.fatigue_analysis(Fmax, Fmin, 99, verbose=True)
print(f"nf = {nf}, ns = {ns}")
print(f"static safety factor = {spring.static_safety_factor()}")
print(f"solid safety factor = {spring.static_safety_factor(solid=True)}")
