"""
Assignment 1 -- Munich Bauhaus Stonehenge -- 02 TOWERS (with the gate)

Inputs
    List Access: points (Point3d), angles, widths, depths, heights  <- 01 Layout
    Item Access: blockiness (int), lean, arch_ratio                 <- sliders
Outputs: out, geometry, colors, tops, tower_colors
    (geometry -> Custom Preview G, colors -> M, tops -> 03 Bridge,
     tower_colors -> 04 Stones)

Relationships
    (heights)  -> FORM + COLOUR by height rank (Kandinsky): the tallest third
                  are yellow triangles, the middle third red squares, the lowest
                  third blue circles.
    blockiness -> MODULAR BLOCKS: the tallest tower gets `blockiness` blocks, the
                  others get blocks in proportion to their height, so every block
                  in the composition is roughly the same height.
    lean       -> LEAN (0..1): 0 steps every tower in evenly; at 1/3 the face
                  toward the court is upright and all setbacks face outward;
                  above that each block overhangs the one below toward the court,
                  so the towers lean in like Marina Bay Sands. At 1 the top block
                  juts out 0.4 x the tower depth past the base.
    (lean)     -> tops: the centre of each top block, which moves with lean, so
                  the bridge always rests on the real tops.
    arch_ratio -> GATE: arch radius = arch_ratio x half the front tower's width,
                  so the half-round gate always fits inside the tower it cuts.
"""

import importlib
import math
import Rhino.Geometry as rg
from System.Drawing import Color
import cdf.geometry_basics as gb
importlib.reload(gb)

FORMS = [("triangle", Color.FromArgb(240, 190, 0)),   # tallest third: yellow
         ("box", Color.FromArgb(200, 30, 30)),        # middle third: red
         ("cylinder", Color.FromArgb(20, 60, 160))]   # lowest third: blue

n = len(points)
blockiness = max(1, int(blockiness or 3))
lean = min(1.0, max(0.0, lean or 0.0))
LEAN_MAX = 3.0      # lean 1 -> align -3: blocks slide past the base toward the court
TOP_SCALE = 0.6     # create_stepped_tower's default top block scale
arch_ratio = 0.6 if arch_ratio is None else min(0.9, max(0.0, arch_ratio))

# FORM + COLOUR by height rank
rank = sorted(range(n), key=lambda i: -heights[i])
forms = [FORMS[rank.index(i) * 3 // n] for i in range(n)]

# MODULAR BLOCKS
tiers = [max(1, round(blockiness * h / max(heights))) for h in heights]

# TOWERS with LEAN: negative align slides upper blocks toward the court
# (local +Y points outward, away from the ring centre)
align = -LEAN_MAX * lean
towers, tops = [], []
for p, a, w, d, h, t, (shape, _) in zip(points, angles, widths, depths, heights, tiers, forms):
    blocks = gb.create_stepped_tower(p, w, d, h, tiers=t, angle=a - math.pi / 2.0,
                                     align=align, shape=shape)
    towers.append(gb.boolean_union(blocks))
    shift = align * (1.0 - (TOP_SCALE if t > 1 else 1.0)) * d / 2.0   # same rule as the top block
    tops.append(rg.Point3d(p.X + shift * math.cos(a), p.Y + shift * math.sin(a), h))

# GATE: half-round arch along Y through the front tower (tower 0)
arch_radius = arch_ratio * widths[0] / 2.0
if arch_radius > 0:
    reach = 2.0 * abs(points[0].Y) + max(depths)
    arch_void = gb.create_cylinder(rg.Point3d(0, -reach, 0), arch_radius, 2.0 * reach, rg.Vector3d.YAxis)
    cut = []
    for tower in towers:
        pieces = []
        for part in tower:
            result = gb.boolean_difference(part, arch_void)
            pieces += list(result) if result else [part]
        cut.append(pieces)
    towers = cut

tower_colors = [color for _, color in forms]   # one per tower, for 04 Stones
geometry, colors = [], []
for tower, (_, color) in zip(towers, forms):
    geometry += tower
    colors += [color] * len(tower)

out = "forms:  {}\nblocks: {}\ngate radius: {:.1f}".format(
    ", ".join(s for s, _ in forms), ", ".join(str(t) for t in tiers), arch_radius)
