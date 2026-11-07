"""
TEMP Grasshopper script -- Assignment 1, Bauhaus composition (Marina Bay Sands
+ Stonehenge ring: stepped towers that slim with height, crossing lintels).
Paste into a Rhino 8 Python 3 Script component. All geometry logic lives in
src/cdf/geometry_basics.py; edits saved in VS Code update live (reload below).

Inputs  (Item Access, float unless noted):
    tower_count (int), spacing_mult, bridge_z, cantilever_len,
    cylinder_radius, cylinder_z_center
Outputs:
    towers, bridge (list of lintels), arch_void, out

Wiring:
    towers + bridge -> Solid Union (flatten the input) -> Solid Difference A
    arch_void                                          -> Solid Difference B

Presets (tower_count, spacing_mult, bridge_z, cantilever_len, cylinder_radius, cylinder_z_center):
    A baseline     : 3, 2.5, 100, 20, 10, 0
    B twin gate    : 4, 1.2,  80, 10, 30, 0
    C wide horizon : 5, 1.8, 140, 60, 12, 0
"""

import importlib
import cdf.geometry_basics as gb
importlib.reload(gb)

result = gb.build_composition(
    tower_count, spacing_mult, bridge_z,
    cantilever_len, cylinder_radius, cylinder_z_center,
)

towers = result["towers"]
bridge = result["bridge"]
arch_void = result["arch_void"]

info = result["info"]
out = "\n".join([
    "towers: {}".format(len(info["heights"])),
    "pitch: {:.2f}  ring radius: {:.2f}".format(info["pitch"], info["ring_radius"]),
    "k: {:.3f}".format(info["k"]),
    "heights: " + ", ".join("{:.1f}".format(h) for h in info["heights"]),
    "extents X: {:.1f} .. {:.1f}".format(info["bridge_x0"], info["bridge_x1"]),
    "pierce: {:.1f} above bridge top {:.1f}".format(info["pierce_amount"], info["bridge_top"]),
])
