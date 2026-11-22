"""
Crocheted Calabi-Yau, step 1 of 3: THE MOULD - Grasshopper Python 3 component.
The fabric (step 2) is crocheted over a Calabi-Yau "mould": the complex curve
    z1^n + z2^n = 1          (n = 5 gives the classic picture)
Hanson's parametrisation: with w = a + i*b, a in [0, pi/2], b in [-b_max, b_max]
    z1 = exp(2*pi*i*k1/n) * cos(w)^(2/n)
    z2 = exp(2*pi*i*k2/n) * sin(w)^(2/n)
Each pair (k1, k2), 0 <= k1, k2 < n, is one patch: n^2 crocheted tiles (25 for n = 5).
A complex curve is a minimal surface in 4D, so its curvature is negative everywhere.

This step plans the ROWS: row 0 (the base chain) is b = 0, and every next row lies one stitch
height higher on the mould (b moves on by stitch_h / stretch, where stretch is how much the
mould is stretched in 4D there). For every row it records how many stitches of width stitch_w
the mould row needs. Growth stops at 'generations' rows or at b_max.

Inputs (Item Access):
    n            : int    (5)      degree of the Fermat curve
    generations  : int    (20)     rows grown on each side of the base chain
    stitch_w     : float  (0.05)   stitch width (4D units)
    stitch_h     : float  (0.05)   stitch height = row height (4D units)
    b_max        : float  (1.5708) growth limit for |b| (pi/2 = the classic full picture)
Outputs:
    mould : the mould object -> input 'mould' of step 2 (Item Access, no type hint)
    info  : text summary
"""

import math
import cmath


class Mould(object):
    """The Calabi-Yau mould and its row plan. Steps 2 and 3 use its methods."""
    DENSE = 240          # samples used to measure the length of one mould row

    def __init__(self, n, generations, stitch_w, stitch_h, b_max):
        self.n, self.generations = n, generations
        self.stitch_w, self.stitch_h, self.b_max = stitch_w, stitch_h, b_max
        self.schedule = self.make_schedule()          # list of (generation, b, stitches needed)
        last_g, last_b = self.schedule[-1][0], self.schedule[-1][1]
        self.stopped_by = "b_max" if (last_b >= b_max - 1e-12 and last_g < generations) else "generations"

    # ---- geometry of the Fermat curve ---------------------------------------------------
    def point4(self, k1, k2, a, b):
        """The 4D point (Re z1, Im z1, Re z2, Im z2) of patch (k1, k2) at w = a + i*b."""
        n, w = self.n, complex(a, b)
        z1 = cmath.exp(2j * math.pi * k1 / n) * cmath.cos(w) ** (2.0 / n)
        z2 = cmath.exp(2j * math.pi * k2 / n) * cmath.sin(w) ** (2.0 / n)
        return (z1.real, z1.imag, z2.real, z2.imag)

    @staticmethod
    def dist4(p, q):
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(p, q)))

    def to_patch(self, p, k1, k2, mirror):
        """Patches differ by a rotation in each complex plane; -b is the complex conjugate.
        So a point of patch (0, 0), b >= 0 can be copied to any patch and side."""
        z1, z2 = complex(p[0], p[1]), complex(p[2], p[3])
        if mirror:
            z1, z2 = z1.conjugate(), z2.conjugate()
        z1 *= cmath.exp(2j * math.pi * k1 / self.n)
        z2 *= cmath.exp(2j * math.pi * k2 / self.n)
        return (z1.real, z1.imag, z2.real, z2.imag)

    def stretch_b(self, b, h=1e-4):
        """Average 4D stretch |dP/db| of the mould along row b."""
        total, m = 0.0, 9
        for s in range(m):
            a = (math.pi / 2.0) * (s + 0.5) / m
            total += self.dist4(self.point4(0, 0, a, b + h), self.point4(0, 0, a, b - h)) / (2.0 * h)
        return total / m

    def row_profile(self, b):
        """Dense samples of mould row b: parameters a and cumulative 4D arc length."""
        D = self.DENSE
        a_s = [(math.pi / 2.0) * i / D for i in range(D + 1)]
        pts = [self.point4(0, 0, a, b) for a in a_s]
        cum = [0.0]
        for p, q in zip(pts, pts[1:]):
            cum.append(cum[-1] + self.dist4(p, q))
        return a_s, cum

    def stitch_params(self, b, stitches):
        """Parameters a of stitches+1 points spread evenly (by arc length) along mould row b."""
        a_s, cum = self.row_profile(b)
        D, L = self.DENSE, cum[-1]
        out, j = [], 0
        for s in range(stitches + 1):
            target = L * s / stitches
            while j < D - 1 and cum[j + 1] < target:
                j += 1
            seg = cum[j + 1] - cum[j]
            t = 0.0 if seg < 1e-15 else min(1.0, max(0.0, (target - cum[j]) / seg))
            out.append(a_s[j] + (a_s[j + 1] - a_s[j]) * t)
        return out

    # ---- the row plan -------------------------------------------------------------------
    def needed(self, b):
        """Stitches the mould row b needs."""
        _, cum = self.row_profile(b)
        return max(1, int(math.ceil(cum[-1] / self.stitch_w)))

    def make_schedule(self):
        sched, b = [(0, 0.0, self.needed(0.0))], 0.0
        for g in range(1, self.generations + 1):
            if b >= self.b_max - 1e-12:
                break
            b = min(self.b_max, b + self.stitch_h / self.stretch_b(b))
            sched.append((g, b, self.needed(b)))
        return sched


mould = Mould(n, generations, stitch_w, stitch_h, b_max)
info = "mould: n {}  patches {}  rows planned {}  b reached {:.3f}  (stopped by {})\nstitches the mould needs per row: {}".format(
    n, n * n, mould.schedule[-1][0], mould.schedule[-1][1], mould.stopped_by,
    [s for _, _, s in mould.schedule])
