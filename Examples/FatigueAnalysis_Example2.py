from FatigueAnalysis import Stress, EnduranceLimit, CalcKf, FatigueAnalysis
from math import pi, sqrt

Sut = 900  # [Mpa]
Sy = 700  # [Mpa]

Ft = 120  # [N]
Fn = 200  # [N]

N = Fn
V = Ft
T = 12 * 1e3  # [Nmm]
My = 5 * Ft
Mz = -100 * Fn
# equivalent moment
Me = sqrt(My ** 2 + Mz ** 2)

d = 16
A = 0.25 * pi * d ** 2
I = 0.25 * pi * (d / 2) ** 4
normal_stress = Stress.UniformStress(N, A)
bending_stress = Stress.BendingStress(Me, I, 8)
torsion_stress = Stress.TorsionStress(T, 8, 2 * I)
shear_stress = Stress.MaxShearStress(V, A, 'circle')
print(f"Normal Stress = {normal_stress}\n"
      f"Bending Stress = {bending_stress}\n"
      f"Torsion Stress = {torsion_stress}\n"
      f"Shear Stress = {shear_stress}")

endurance_limit = EnduranceLimit(Sut=Sut, surface_finish='machined', rotating=True, max_bending_stress=bending_stress,
                                 max_normal_stress=normal_stress, material='steel', stress_type="multiple", temp=25,
                                 reliability=99, diameter=16)

print(f"Se'={endurance_limit.unmodified}, Se={endurance_limit.modified:.2f}")
endurance_limit.getFactors()

# dynamic stress concentration factors
Kf = CalcKf(0.9, 1.32)
Kfs = CalcKf(0.95, 1.12)

print(f"Kf={Kf:.3f}, Kfs={Kfs:.3f}")

fatigue_analysis = FatigueAnalysis(Sut=Sut, Sy=Sy, ductile=True, Kf_bending=Kf, Kf_torsion=Kfs,
                                   endurance_limit=endurance_limit,
                                   alternating_bending_stress=bending_stress,
                                   mean_torsion_stress=torsion_stress)

print(f"Mean Equivalent Stress={fatigue_analysis.mean_equivalent_stress}\n"
      f"Alternating Equivalent Stress={fatigue_analysis.alternating_equivalent_stress}\n")

nF, nl = fatigue_analysis.GetSafetyFactor('Modified Goodman', verbose=True)
print()

# miner for time to failure every group is of the following structure:
# [freq[Hz], alternating stresses, mean stresses]
# Note: In this case the stresses in the groups are alternating and mean (instead of the default max and min)
#       so the alt_mean flag should be True, and because we use frequency instead of number of repetitions
# the freq flag should be true
stresses = [[2, 700, 500], [5, 400, 540], [3, 900, -200]]
N_total = fatigue_analysis.Miner(stresses, Sut=1500, Se=750, alt_mean=True, verbose=True, freq=True)
