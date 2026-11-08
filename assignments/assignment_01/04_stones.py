"""
Assignment 1 -- Munich Bauhaus Stonehenge -- 04 STONES

Inputs
    List Access: angles, widths, depths, heights  <- 01 Layout
                 tower_colors (Color)             <- 02 Towers
    Item Access: radius                           <- 01 Layout
                 stones (int), ruin               <- sliders
Outputs: out, geometry, colors   (geometry -> Custom Preview G, colors -> M)

Relationships
    stones    -> STONE RING: up to `stones` standing stones fill each gap between
                 two towers, evenly spaced on the same circle; fewer if the gap
                 is too narrow (spacing >= STONE_GAP x stone width).
    (heights) -> stone height = STONE_RATIO x the lower of the two towers it
                 stands between, so the small ring echoes the big one; width,
                 depth and lintel thickness are fixed fractions of that height.
    (stones)  -> SMALL TRILITHONS: every pair of neighbouring stones carries a
                 flat lintel.
    ruin      -> RUIN: that fraction of stones (0..1, fixed SEED) has fallen
                 outward and lies on the plinth; its lintel is gone.
    (tower_colors) -> COLOUR: each stone takes the colour of the nearer of the
                 two towers it stands between: each gap switches colour halfway,
                 so the Kandinsky rule of the towers carries into the small
                 ring; lintels stay black like the bridge.
"""

import importlib
import math
import random
import Rhino.Geometry as rg
from System.Drawing import Color
import cdf.geometry_basics as gb
importlib.reload(gb)

STONE_RATIO, STONE_GAP, SEED = 0.25, 1.6, 7
STONE_W, STONE_D, STONE_LINTEL = 0.45, 0.25, 0.15   # x stone height (Stonehenge proportions)
BLACK = Color.FromArgb(30, 30, 30)

n = len(angles)
stones = 4 if stones is None else max(0, int(stones))
ruin = min(1.0, max(0.0, ruin or 0.0))


def on_ring(a, r, z=0.0):
    return rg.Point3d(r * math.cos(a), r * math.sin(a), z)


rng = random.Random(SEED)   # decides which stones fall
geometry, colors = [], []
for i in range(n):
    j = (i + 1) % n
    stone_h = STONE_RATIO * min(heights[i], heights[j])
    sw, sd = STONE_W * stone_h, STONE_D * stone_h
    clear_i = (math.hypot(widths[i], depths[i]) / 2.0 + sw) / radius   # keep clear of the towers
    clear_j = (math.hypot(widths[j], depths[j]) / 2.0 + sw) / radius
    gap = (angles[j] - angles[i]) % (2.0 * math.pi)   # gaps differ with asymmetry
    a0, a1 = angles[i] + clear_i, angles[i] + gap - clear_j
    if a1 <= a0:
        continue
    count = min(stones, int((a1 - a0) * radius / (STONE_GAP * sw)) + 1)
    ring = [a0 + (a1 - a0) * (s + 0.5) / count for s in range(count)]
    fallen = [rng.random() < ruin for _ in ring]
    for a, down in zip(ring, fallen):
        colors.append(tower_colors[i] if a - angles[i] < gap / 2.0 else tower_colors[j])  # nearer tower
        if down:  # lying on its side, toppled outward
            geometry.append(gb.create_box(on_ring(a, radius + stone_h / 2.0), sw, stone_h, sd, a - math.pi / 2.0))
        else:
            geometry.append(gb.create_box(on_ring(a, radius), sw, sd, stone_h, a - math.pi / 2.0))
    for s in range(0, count - 1, 2):  # lintel on each standing pair
        if fallen[s] or fallen[s + 1]:
            continue
        p0, p1 = on_ring(ring[s], radius, stone_h), on_ring(ring[s + 1], radius, stone_h)
        along = p1 - p0
        along.Unitize()
        geometry.append(gb.create_beam(p0 - along * sw / 2.0, p1 + along * sw / 2.0, sd, STONE_LINTEL * stone_h))
        colors.append(BLACK)

out = "stone parts: {}".format(len(geometry))
