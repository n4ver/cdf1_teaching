"""
Assignment 1 -- Munich Bauhaus Stonehenge -- 01 LAYOUT
A ring of stepped towers (Marina Bay Sands) carrying sloped lintels on their
tops (Stonehenge trilithons), a ring of standing stones in between, a round
plinth, and a gate through the front tower.

Canvas (one Python 3 component per file, each output -> its own Custom Preview):

    sliders -> 01 Layout -+-> 02 Towers -> Custom Preview
                          |       +-- tops --> 03 Bridge + SkyPark -> Custom Preview
                          +-> 04 Stones -> Custom Preview
                          +-> 05 Plinth -> Custom Preview

This component
    Inputs  (Item Access): tower_count (int), spacing_mult, bridge_z, asymmetry,
                           contrast
    Outputs: out, points, angles, widths, depths, heights, radius

Relationships
    tower_count  -> footprints cycle W_FACTORS (3) against D_FACTORS (4), so the
                    rhythm of widths and depths only repeats after 12 towers.
    contrast     -> EQUAL VOLUME, softened: height = k * (VOLUME / footprint)^contrast.
                    1 is strict equal volume (a slim tower is a tall one);
                    0.5 softens the differences; 0 makes all towers equal.
    bridge_z     -> k is chosen so the shortest tower is exactly bridge_z tall:
                    it sets the lowest lintel and scales every tower.
    spacing_mult -> RING: the gap between towers is spacing_mult x the widest
                    tower, which sets the ring radius; towers never collide.
                    Tower 0 stands at the front (-Y).
    asymmetry    -> DYNAMIC BALANCE (0..0.8): the gaps between towers grow
                    steadily around the ring, from (1 - asymmetry) to
                    (1 + asymmetry) x the average gap. 0 is a regular ring; higher
                    values cluster the towers on one side and open the other.
                    The ring radius grows so the TIGHTEST gap still equals
                    spacing_mult x the widest tower.
"""

import math
import Rhino.Geometry as rg

BASE_W, BASE_D = 40.0, 30.0
W_FACTORS = [1.00, 1.35, 0.70]
D_FACTORS = [1.00, 0.70, 1.25, 0.90]
VOLUME = 60000.0

n = max(3, int(tower_count or 3))
spacing_mult = max(1.05, spacing_mult or 2.5)
bridge_z = max(10.0, bridge_z or 60.0)
asymmetry = min(0.8, max(0.0, asymmetry or 0.0))
contrast = 1.0 if contrast is None else min(1.0, max(0.0, contrast))

# EQUAL VOLUME, shortest tower = bridge_z
widths = [BASE_W * W_FACTORS[i % 3] for i in range(n)]
depths = [BASE_D * D_FACTORS[i % 4] for i in range(n)]
raw = [(VOLUME / (w * d)) ** contrast for w, d in zip(widths, depths)]
k = bridge_z / min(raw)
heights = [k * h for h in raw]

# RING with DYNAMIC BALANCE: gap i (tower i -> i+1) has weight 1 - a ... 1 + a
weights = [1.0 + asymmetry * (2.0 * i / (n - 1) - 1.0) for i in range(n)]
gaps = [2.0 * math.pi * wt / n for wt in weights]          # weights sum to n
pitch = spacing_mult * max(widths)
radius = pitch / (2.0 * math.sin(min(gaps) / 2.0)) + max(depths) / 2.0
angles = [-math.pi / 2.0 + sum(gaps[:i]) for i in range(n)]
points = [rg.Point3d(radius * math.cos(a), radius * math.sin(a), 0) for a in angles]

out = "towers: {}  ring radius: {:.1f}  k: {:.2f}\nheights: {}".format(
    n, radius, k, ", ".join("{:.1f}".format(h) for h in heights))
