from math import exp
from me_toolbox.fasteners import ThreadedFastener
from me_toolbox.fasteners import MetricBolt
from me_toolbox.fasteners import UnBolt

d = 12
bolt = MetricBolt(d, 1.75, 'e', 3, 75)
# bolt = UnBolt(3 / 8, 24, True, 3, True, 1)

thickness = [25, 7, 25]
elastic = [153e3, 128e3, 207e3]

layers = [(t, E) for t, E in zip(thickness, elastic)]
grip_len = sum(thickness)
fastener = ThreadedFastener(bolt, grip_len, layers)
km = fastener.substrate_stiffness
kb = fastener.bolt_stiffness
k = fastener.fastener_stiffness
print(f"km={km}\nkb={kb}\nk={k}")
