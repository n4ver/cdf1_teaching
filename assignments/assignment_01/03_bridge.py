"""
Assignment 1 -- Munich Bauhaus Stonehenge -- 03 BRIDGE + SKYPARK

Inputs
    List Access: tops (Point3d)   <- 02 Towers
                 angles           <- 01 Layout
    Item Access: radius           <- 01 Layout
                 overhang         <- slider (0..100 m)
Outputs: out, geometry, colors   (geometry -> Custom Preview G, colors -> M)

Relationships
    (tops)    -> TRILITHONS: lintel i rests on the top blocks of towers i and
                 i+1, so it slopes by their height difference and follows the
                 towers when they lean. Lintels are black. Where a lintel meets
                 a SkyPark tower it rests on the deck instead, never through it.
    (tops)    -> SKYPARK (Marina Bay Sands): the lintel between the TALLEST PAIR
                 OF NEIGHBOURS (highest lower top) becomes a level white deck,
                 laid on the lower of the two tops; the taller tower rises
                 through it as a crown.
    (angles)  -> CANTILEVER SIDE: the deck cantilevers from the end nearer the
                 widest gap in the ring (the opening made by `asymmetry`), so the
                 MBS cantilever points at the open side of the composition.
    overhang  -> CANTILEVER: that end reaches `overhang` metres past its tower;
                 the other end stops SKYPARK_MARGIN past its tower.
"""

import importlib
import math
import Rhino.Geometry as rg
from System.Drawing import Color
import cdf.geometry_basics as gb
importlib.reload(gb)

LINTEL_WIDTH, LINTEL_THICK = 10.0, 6.0
SKYPARK_W, SKYPARK_THICK, SKYPARK_MARGIN = 18.0, 5.0, 8.0
BLACK, WHITE = Color.FromArgb(30, 30, 30), Color.FromArgb(235, 235, 230)

n = len(tops)
overhang = 40.0 if overhang is None else max(0.0, overhang)

# SKYPARK pair: neighbours i, i+1 whose LOWER top is highest
sky = max(range(n), key=lambda i: min(tops[i].Z, tops[(i + 1) % n].Z))

# CANTILEVER SIDE: the middle of the widest gap between neighbouring towers
gaps = [(angles[(i + 1) % n] - angles[i]) % (2.0 * math.pi) for i in range(n)]
w = max(range(n), key=lambda i: gaps[i])
open_a = angles[w] + gaps[w] / 2.0

t0, t1 = tops[sky], tops[(sky + 1) % n]
deck_z = min(t0.Z, t1.Z)
p0, p1 = rg.Point3d(t0.X, t0.Y, deck_z), rg.Point3d(t1.X, t1.Y, deck_z)
open_pt = rg.Point3d(radius * math.cos(open_a), radius * math.sin(open_a), deck_z)
near, far = (p0, p1) if p0.DistanceTo(open_pt) < p1.DistanceTo(open_pt) else (p1, p0)

along = near - far
along.Unitize()
geometry = [gb.create_beam(far - along * SKYPARK_MARGIN, near + along * overhang,
                           SKYPARK_W, SKYPARK_THICK)]
colors = [WHITE]


def seat(k):
    """Where a lintel sits on tower k: its top, or the deck surface if higher."""
    p = tops[k]
    if k in (sky, (sky + 1) % n):
        return rg.Point3d(p.X, p.Y, max(p.Z, deck_z + SKYPARK_THICK))
    return p


for i in range(n):  # TRILITHONS, except the pair that carries the SkyPark
    if i != sky:
        geometry.append(gb.create_beam(seat(i), seat((i + 1) % n), LINTEL_WIDTH, LINTEL_THICK))
        colors.append(BLACK)

out = "skypark on towers {} and {}  deck z: {:.1f}  crown: {:.1f}  overhang: {:.1f}".format(
    sky, (sky + 1) % n, deck_z, abs(t0.Z - t1.Z), overhang)
