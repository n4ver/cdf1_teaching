"""
Crocheted Calabi-Yau, step 2 of 3: THE CROCHET - Grasshopper Python 3 component.
Grows a hyperbolic fabric over the mould from step 1, row by row, with crochet rules
(crochet pattern "Hyperbolic Surface": base chain, then rows, turn work).

    GENERATION 0 - BASE CHAIN: the row b = 0 of the mould, cut into stitches.
    EVERY NEW GENERATION g crochets one new row on each side (+b and -b), one stitch higher:
      1. increase: the row gets  (stitches the mould row needs) * increase^g  stitches.
         increase = 1 -> the fabric fits the mould exactly.
         increase > 1 -> every row has more stitches than the mould has room for, and the
         excess grows exponentially - the crochet "increase" that makes surfaces hyperbolic.
      2. stitch: every new stitch is worked into the stitch below it (it starts where that stitch
         really is), joined to it by a post spring (one stitch high) and to its neighbours by row
         springs (one stitch wide). The two ends of every row are sewn to the edges of the patch,
         so neighbouring tiles stay joined.
      3. relax: springs keep each stitch its size, 'pull' draws every stitch towards its place
         on the mould. The newest 'active_rows' rows move; older rows have set.
         The extra stitches do not fit, so the fabric ruffles around the Calabi-Yau.
    Growth stops at the end of the mould's row plan or when a row would need more than
    max_stitches stitches.
The relaxation happens in 4D. All patches are exact 4D rotations / mirror images of each other, so
only one half-patch (k1 = k2 = 0, b >= 0) is grown; step 3 copies it. Fixed seed: same inputs,
same fabric, so animating 'generations' in step 1 plays the growth.

Inputs (Item Access):
    mould        : object          output 'mould' of step 1 (no type hint)
    increase     : float  (1.06)   stitch excess per row (1 = no ruffles)
    pull         : float  (0.05)   0..1, how strongly the fabric follows the mould
    iterations   : int    (20)     relaxation steps after each new row
    active_rows  : int    (3)      how many of the newest rows still move
    seed         : int    (1)      seed for the small offsets that let the fabric ruffle
    max_stitches : int    (600)    safety limit: stitches in one row of one patch
Outputs:
    fabric : the grown fabric -> input 'fabric' of step 3 (Item Access, no type hint)
    counts : stitches per generation, summed over all patches (plug into a Quick Graph)
    info   : text summary
"""

import math
import random


class Fabric(object):
    """The grown half-patch. rows = list of (generation, b, vertex indices);
    P = relaxed 4D stitch positions, T = their target points on the mould."""

    def __init__(self, mould, rows, P, T, stopped_by):
        self.mould, self.rows, self.P, self.T, self.stopped_by = mould, rows, P, T, stopped_by


def grow_half(mould, increase, pull, iterations, active_rows, seed, max_stitches):
    rng = random.Random(seed)
    dist4, stitch_w = mould.dist4, mould.stitch_w
    P, T, pinned, row_of = [], [], [], []
    rows, row_springs = [], []
    stopped_by = mould.stopped_by

    for g, b, need in mould.schedule:
        c = need if g == 0 else int(math.ceil(need * increase ** g))
        if c > max_stitches:
            stopped_by = "max_stitches"
            break
        idx = []
        prev = rows[-1][2] if rows else None
        for j, a in enumerate(mould.stitch_params(b, c)):
            t = mould.point4(0, 0, a, b)
            pin = g == 0 or j == 0 or j == c          # base chain + seams are sewn to the mould
            jit = 0.0 if pin else 0.3 * stitch_w
            # worked into the stitch below: start where that stitch really is, not on the mould
            off = [0.0] * 4
            if prev and not pin:
                q = prev[int(round(j * (len(prev) - 1) / float(c)))]
                off = [P[q][m] - T[q][m] for m in range(4)]
            P.append([t[m] + off[m] + rng.uniform(-jit, jit) for m in range(4)])
            T.append(t)
            pinned.append(pin)
            row_of.append(len(rows))
            idx.append(len(P) - 1)

        springs = []
        for j in range(c):                                   # one stitch wide
            springs.append((idx[j], idx[j + 1], stitch_w, 1.0))
        for j in range(c - 1):                               # weak: keeps the row smooth
            springs.append((idx[j], idx[j + 2], 2.0 * stitch_w, 0.15))
        if prev:                                             # posts into the row below
            cp = len(prev) - 1
            for j in range(c + 1):
                q = prev[int(round(j * cp / float(c)))]
                springs.append((q, idx[j], dist4(T[q], T[idx[j]]), 1.0))
        rows.append((g, b, idx))
        row_springs.append(springs)

        if g > 0:
            relax(P, T, pinned, row_of, rows, row_springs, pull, iterations, active_rows)
    return Fabric(mould, rows, P, T, stopped_by)


def relax(P, T, pinned, row_of, rows, row_springs, pull, iterations, active_rows):
    """Move the newest rows: springs keep stitch sizes, 'pull' draws stitches to the mould."""
    first = max(1, len(rows) - active_rows)
    springs = [s for r in range(first, len(rows)) for s in row_springs[r]]
    verts = [v for r in range(first, len(rows)) for v in rows[r][2] if not pinned[v]]

    def free(v):
        return not pinned[v] and row_of[v] >= first

    for _ in range(iterations):
        for i, j, rest, k in springs:
            a, b = P[i], P[j]
            d = [b[m] - a[m] for m in range(4)]
            L = math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2] + d[3] * d[3])
            if L < 1e-12:
                continue
            fi, fj = free(i), free(j)
            if not (fi or fj):
                continue
            move = k * (L - rest) / L
            if fi and fj:
                move *= 0.5
            for m in range(4):
                if fi:
                    a[m] += d[m] * move
                if fj:
                    b[m] -= d[m] * move
        for v in verts:
            p, t = P[v], T[v]
            for m in range(4):
                p[m] += pull * (t[m] - p[m])


# ---- grow -------------------------------------------------------------------------------
fabric = grow_half(mould, increase, pull, iterations, active_rows, seed, max_stitches)
patches = mould.n * mould.n
counts = [patches * (len(idx) - 1) * (1 if g == 0 else 2) for g, b, idx in fabric.rows]
info = "crochet: generations {}  (stopped by {})  stitches per row per patch {} -> {}  total {}".format(
    fabric.rows[-1][0], fabric.stopped_by, len(fabric.rows[0][2]) - 1, len(fabric.rows[-1][2]) - 1,
    sum(counts))
