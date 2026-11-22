"""Angular tree-stump floor pattern - self-contained Grasshopper Python 3 component.
A floor with PREDEFINED WALLS (an ASCII plan, '#' = wall, '.' = floor) is covered with the
growth rings of tree stumps - but angular: every ring is an octagon, so all edges run at
0 / 45 / 90 degrees.

How it works
    1. STUMPS: the distance of every floor cell to the nearest wall is computed; each
       deep local maximum of that field (the middle of a room) becomes a stump centre.
    2. ONE FIELD: f(p) = the smallest octagonal distance from p to any stump. The rings are
       the contour lines of f at fixed radii (spacing follows a light / dark rhythm of
       1.0, 0.75, 1.25 x pitch, like early and late wood). Because it is ONE field, the
       pattern is continuous: where two stumps meet their rings merge into one unbroken line
       with a sharp angle, and the lines flow through doorways from room to room.
    3. CLIPPING: lines are cut only where they would enter a wall, so every line is either
       closed or runs wall to wall; the curves are joined into the longest possible chains.
       Curves are flat (z = 0, no thickness) and never enter a wall cell.
Fully deterministic: no randomness.

Inputs (Item Access):
    cell      : float  (1.0)   cell size
    pitch     : float  (0.5)   average distance between rings, in cells
    wall_h    : float  (0.5)   wall height, in cells
    plan      : str    (None)  optional ASCII floor plan, one row per line, top row first.
                               '#' = wall, anything else = floor. None = built-in plan.
Outputs:
    curves        : ring curves (flat, on the floor)
    centres       : stump centres
    floor         : mesh of the floor cells
    walls         : mesh of the wall blocks
    grid          : floor cell outline as lines
    info          : text summary

Canvas:  sliders/panel -> this component -> Custom Preview (floor, walls) + curves
"""
import math
import Rhino.Geometry as rg

# ----------------------------------------------------------------------------------------
# PREDEFINED WALLS (24 x 16, top row first). Two side rooms, a central room, a hall with a
# 2x2 pillar, doorways between them. Symmetric left-right and top-bottom.
DEFAULT_PLAN = """
########################
#.....#..........#.....#
#.....#..........#.....#
#.....#..........#.....#
#.....#..........#.....#
#.....#..........#.....#
#..####..........####..#
#..........##..........#
#..........##..........#
#..####..........####..#
#.....#..........#.....#
#.....#..........#.....#
#.....#..........#.....#
#.....#..........#.....#
#.....#..........#.....#
########################
"""

# ---- floor plan -------------------------------------------------------------------------
text = plan if (plan and str(plan).strip()) else DEFAULT_PLAN
rows = [r for r in str(text).replace("\r", "").split("\n") if r.strip() != ""]
H = len(rows)
W = max(len(r) for r in rows)
rows = [r.ljust(W, "#") for r in rows]
WALL = set()
for ri, r in enumerate(rows):
    y = H - 1 - ri                                # top row of the text = highest y
    for x, ch in enumerate(r):
        if ch == "#":
            WALL.add((x, y))


def is_wall(x, y):
    return x < 0 or y < 0 or x >= W or y >= H or (x, y) in WALL


FLOOR = [(x, y) for y in range(H) for x in range(W) if (x, y) not in WALL]

# ---- stump centres: local maxima of the distance to the nearest wall --------------------
N8 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
dist = {}
frontier = [c for c in FLOOR if any(is_wall(c[0] + a, c[1] + b) for a, b in N8)]
for c in frontier:
    dist[c] = 1
while frontier:
    nxt = []
    for (x, y) in frontier:
        for a, b in N8:
            n = (x + a, y + b)
            if n not in dist and not is_wall(*n):
                dist[n] = dist[(x, y)] + 1
                nxt.append(n)
    frontier = nxt

deepest = max(dist.values())
# only the deep peaks (one per room); shallow ones in doorways and halls are not stumps
peaks = {c for c in FLOOR if dist[c] >= 0.75 * deepest
         and all(dist[c] >= dist.get((c[0] + a, c[1] + b), 0) for a, b in N8)}
centres_xy, seen = [], set()
for c in sorted(peaks, key=lambda c: (c[1], c[0])):
    if c in seen:
        continue
    comp, stack = [], [c]
    seen.add(c)
    while stack:                                   # plateau of equal distance
        p = stack.pop()
        comp.append(p)
        for a, b in N8:
            n = (p[0] + a, p[1] + b)
            if n in peaks and n not in seen and dist[n] == dist[c]:
                seen.add(n)
                stack.append(n)
    centres_xy.append((sum(p[0] for p in comp) / float(len(comp)) + .5,
                       sum(p[1] for p in comp) / float(len(comp)) + .5))


# ---- one continuous field: smallest octagonal distance to any stump ---------------------
def octo(dx, dy):
    dx, dy = abs(dx), abs(dy)
    return max(dx, dy, (dx + dy) / 1.5)


# ties between equally near stumps go to the one nearer the plan centre (keeps symmetry)
ORDER = sorted(range(len(centres_xy)),
               key=lambda i: (round((centres_xy[i][0] - W / 2.0) ** 2 + (centres_xy[i][1] - H / 2.0) ** 2, 9), i))
RANK = {i: n for n, i in enumerate(ORDER)}


def owner_of(px, py):
    return min(range(len(centres_xy)),
               key=lambda i: (round(octo(px - centres_xy[i][0], py - centres_xy[i][1]), 9), RANK[i]))


EPS = 1e-9
RHYTHM = (1.0, 0.75, 1.25)                         # light / dark growth rhythm


def octagon(cx, cy, r):
    o = [(r, -r / 2), (r, r / 2), (r / 2, r), (-r / 2, r), (-r, r / 2), (-r, -r / 2), (-r / 2, -r), (r / 2, -r)]
    return [(cx + a, cy + b) for a, b in o]


def on_floor(a, b):
    """Is the straight piece a-b (inside one cell, or on a grid line) next to a floor cell?"""
    mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    if abs(a[0] - b[0]) < EPS and abs(a[0] - round(a[0])) < EPS:      # on a vertical grid line
        cells = [(int(round(a[0])) - 1, int(math.floor(my))), (int(round(a[0])), int(math.floor(my)))]
    elif abs(a[1] - b[1]) < EPS and abs(a[1] - round(a[1])) < EPS:    # on a horizontal grid line
        cells = [(int(math.floor(mx)), int(round(a[1])) - 1), (int(math.floor(mx)), int(round(a[1])))]
    else:
        cells = [(int(math.floor(mx)), int(math.floor(my)))]
    return any(not is_wall(*c) for c in cells)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def mine(i, a, b, t):
    p = lerp(a, b, t)
    return owner_of(p[0], p[1]) == i


def own_intervals(i, a, b):
    """Parameter intervals of a-b where stump i is the nearest one (bisected to ~1e-12)."""
    n = max(4, int(math.hypot(b[0] - a[0], b[1] - a[1]) * 48))
    ts = [k / float(n) for k in range(n + 1)]
    flags = [mine(i, a, b, t) for t in ts]
    out, start = [], (0.0 if flags[0] else None)
    for k in range(n):
        if flags[k] != flags[k + 1]:
            lo, hi = ts[k], ts[k + 1]
            for _ in range(48):
                mid = (lo + hi) / 2.0
                if mine(i, a, b, mid) == flags[k]:
                    lo = mid
                else:
                    hi = mid
            t = (lo + hi) / 2.0
            if flags[k]:
                out.append((start, t))
                start = None
            else:
                start = t
    if start is not None:
        out.append((start, 1.0))
    return out


def clipped_edge(i, a, b):
    ts = {0.0, 1.0}
    for k in (0, 1):
        d = b[k] - a[k]
        if abs(d) > EPS:
            lo, hi = sorted((a[k], b[k]))
            for g in range(int(math.floor(lo)) + 1, int(math.ceil(hi))):
                ts.add((g - a[k]) / d)
    ts = sorted(t for t in ts if -EPS <= t <= 1 + EPS)
    pieces = []
    for t0, t1 in zip(ts, ts[1:]):
        p, q = lerp(a, b, t0), lerp(a, b, t1)
        if not on_floor(p, q):
            continue
        for u0, u1 in own_intervals(i, p, q):
            if u1 - u0 > 1e-9:
                pieces.append((lerp(p, q, u0), lerp(p, q, u1)))
    return pieces


radii, r, k = [], 0.25 * pitch, 0
while r < 1.5 * max(W, H):
    radii.append(r)
    r += pitch * RHYTHM[k % len(RHYTHM)]
    k += 1

ring_segments = []                                  # (stump, ring, p, q)
for i, (cx, cy) in enumerate(centres_xy):
    for ri, r in enumerate(radii):
        v = octagon(cx, cy, r)
        for a, b in zip(v, v[1:] + v[:1]):
            for p, q in clipped_edge(i, a, b):
                ring_segments.append((i, ri, p, q))

# ---- Rhino geometry ---------------------------------------------------------------------
Z = 0.0


def P(p, z=Z):
    return rg.Point3d(p[0] * cell, p[1] * cell, z)


tol = 1e-4 * cell
pieces = [rg.LineCurve(P(p), P(q)) for _, _, p, q in ring_segments]
curves = list(rg.Curve.JoinCurves(pieces, tol) or pieces)       # one unbroken line wherever rings touch
centres = [P(c) for c in centres_xy]

# floor: one quad per floor cell
floor = rg.Mesh()
for (x, y) in FLOOR:
    v = floor.Vertices.Count
    for dx, dy in ((0, 0), (1, 0), (1, 1), (0, 1)):
        floor.Vertices.Add((x + dx) * cell, (y + dy) * cell, -0.001 * cell)
    floor.Faces.AddFace(v, v + 1, v + 2, v + 3)
floor.Normals.ComputeNormals()

# walls: one solid block per wall cell
walls = rg.Mesh()
for (x, y) in sorted(WALL):
    box = rg.Box(rg.Plane.WorldXY, rg.Interval(x * cell, (x + 1) * cell),
                 rg.Interval(y * cell, (y + 1) * cell), rg.Interval(0, wall_h * cell))
    walls.Append(rg.Mesh.CreateFromBox(box, 1, 1, 1))
walls.Normals.ComputeNormals()

# grid: unique edges of floor cells
edges = set()
for (x, y) in FLOOR:
    edges.update([((x, y), (x + 1, y)), ((x + 1, y), (x + 1, y + 1)), ((x, y + 1), (x + 1, y + 1)), ((x, y), (x, y + 1))])
grid = [rg.LineCurve(P(a), P(b)) for a, b in sorted(edges)]

info = "grid {}x{}  floor cells {}  wall cells {}  stumps {}  rings per stump {}  curves {}".format(
    W, H, len(FLOOR), len(WALL), len(centres_xy), len(radii), len(curves))
