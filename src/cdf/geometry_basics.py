"""
Geometry basics -- reusable Rhino.Geometry functions for Grasshopper.

Adding a new function with Copilot
-----------------------------------
1. Open this file and select this chat model, then ask Copilot something like:
   "Add a function here, all in Rhino geometry, that builds a <your shape/idea>.
   Follow the same style as create_cone / create_fractal_tree (defaults for
   optional inputs, a docstring listing params, return a Rhino.Geometry object)."
2. Once the function is added, ask Copilot:
   "Give me the Python code to use this function in a Grasshopper GHPython 3
   component, importing it from computational_design_and_fabrication."
3. Copy the snippet Copilot gives you into a GHPython component, wire up the
   inputs as sliders/panels, and set the output variable (e.g. `a`).
"""

import math
import Rhino.Geometry as rg


def create_cone(base_point=None, height=10.0, radius=5.0, cap_bottom=True):
    """
    Build a cone as a Brep.

    base_point : Rhino.Geometry.Point3d -- center of the cone's base circle
    height     : float -- cone height along the base plane's normal (Z by default)
    radius     : float -- base circle radius
    cap_bottom : bool  -- whether to cap the base circle (closed vs open cone)

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)

    plane = rg.Plane(base_point, rg.Vector3d.ZAxis)
    cone = rg.Cone(plane, height, radius)
    return cone.ToBrep(cap_bottom)

def create_sphere(base_point=None, radius=5.0):
    """
    Build a sphere as a Brep.
    
    base_point: Rhino.Geometry.Point3d -- Center of the sphere
    radius: float -- Sphere radius

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0,0,0)

    sphere = rg.Sphere(base_point, radius)
    
    return sphere.ToBrep()

def boolean_difference(brep_a, brep_b):
    """
    Perform a boolean difference operation between two Breps.

    brep_a : Rhino.Geometry.Brep -- the first Brep
    brep_b : Rhino.Geometry.Brep -- the second Brep to subtract from the first

    Returns a list of Rhino.Geometry.Brep resulting from the difference.
    """
    if brep_a is None or brep_b is None:
        raise ValueError("Both brep_a and brep_b must be provided.")

    result = rg.Brep.CreateBooleanDifference(brep_a, brep_b, 0.001)
    return result


def copy_brep_along_z(brep, distance, copy_count):
    """
    Create copies of a Brep, each offset in the +Z direction.

    brep : Rhino.Geometry.Brep -- the Brep to copy
    distance : float -- the Z spacing between consecutive copies
    copy_count : int -- the number of copies to create

    Returns a list of Rhino.Geometry.Brep copies; copy i is moved by distance * (i + 1).
    """
    if brep is None:
        raise ValueError("brep must be provided.")
    if copy_count < 0:
        raise ValueError("copy_count must not be negative.")

    copies = []
    for i in range(1, int(copy_count) + 1):
        copy = brep.DuplicateBrep()
        copy.Transform(rg.Transform.Translation(rg.Vector3d(0, 0, distance * i)))
        copies.append(copy)
    return copies


# =============================================================================
# Assignment 1 -- Bauhaus composition inspired by Marina Bay Sands + Stonehenge
# =============================================================================
#
# Parameters (Grasshopper inputs)
#   tower_count        number of towers standing in the ring (>= 3)
#   spacing_mult       clear gap between neighbouring towers, as a multiple of
#                      the widest footprint (sets the ring radius)
#   bridge_z           underside height of the lintel ring
#   cantilever_len     how far each lintel runs past the towers it rests on
#   cylinder_radius    radius of the arch void cut through the base
#   cylinder_z_center  height of the arch void axis (0 = half-round arch)
#
# Relationships
#   1. Constant volume: every tower holds the same volume, so height is
#      inversely proportional to footprint area (h = k * V / (w * d * fill)).
#   2. Setback taper: each tower is TIERS stacked boxes shrinking linearly to
#      TOP_SCALE, so towers get slimmer as they rise toward the lintels.
#   3. Pierce rule: one uniform k lifts all towers until the tallest pierces
#      the lintel top by PIERCE_MARGIN and the shortest reaches the lintels.
#   4. Ring: towers face the centre; the ring radius grows with spacing_mult
#      and the widest tower, so towers never collide.
#   5. Lintels: one box per pair of neighbours (a trilithon), extended by
#      cantilever_len past both towers so the beams cross above each tower.
#   6. Accents cycle by tower index (i % 3): cantilever / drum / plinth + fin.
#   7. The arch void runs along Y through the ring, centred on the real
#      extents of all parts; tower 0 sits on +Y so its base is always cut.
#
# The pure layout math (no Rhino) comes first so it can be unit-tested in
# plain Python; the Rhino.Geometry layer below only converts it to Breps.
# Part specs: ("box", (cx, cy, theta, sx, sy, z0, z1)) -- box centred on
# (cx, cy) in plan, rotated by theta, size sx along its local X, sy along its
# local Y -- or ("cyl", (xc, yc, z0, height, radius)).

BASE_W = 40.0
BASE_D = 30.0
TARGET_VOLUME = 60000.0
BRIDGE_THICK = 8.0
PIERCE_MARGIN = 15.0
CYL_OVERSHOOT = 2.0
W_FACTORS = [1.00, 1.35, 0.70]
D_FACTORS = [1.00, 0.70, 1.25, 0.90]
TIERS = 3           # stepped setbacks per tower
TOP_SCALE = 0.6     # top tier width/depth as a fraction of the base tier
LINTEL_DEPTH = 16.0
OVERLAP = 2.0       # min embed between touching parts (robust Solid Union)


# --- A) Pure-Python layout math ----------------------------------------------

def tower_footprints(
    n: int,
    base_w: float = BASE_W,
    base_d: float = BASE_D,
    w_factors: list[float] = W_FACTORS,
    d_factors: list[float] = D_FACTORS,
) -> list[tuple[float, float]]:
    """
    Base footprint (w, d) of each tower: base size scaled by cycling factor
    lists. Different list lengths (3 vs 4) give a non-repeating rhythm.
    """
    return [
        (base_w * w_factors[i % len(w_factors)], base_d * d_factors[i % len(d_factors)])
        for i in range(n)
    ]


def tier_scales(tiers: int = TIERS, top_scale: float = TOP_SCALE) -> list[float]:
    """
    Footprint scale of each tier, shrinking linearly from 1.0 at the ground
    to top_scale at the top: the tower slims as Z increases.
    """
    if tiers <= 1:
        return [1.0]
    return [1.0 - j * (1.0 - top_scale) / (tiers - 1) for j in range(tiers)]


def tower_heights(
    footprints: list[tuple[float, float]],
    target_volume: float,
    bridge_z: float,
    bridge_thick: float,
    pierce_margin: float,
    min_embed: float = 0.0,
    scales: list[float] = (1.0,),
) -> tuple[list[float], float]:
    """
    Height is inversely proportional to footprint (equal volume, corrected by
    the tier fill mean(s^2)), times one uniform k so the tallest pierces the
    bridge top by pierce_margin and the shortest reaches bridge_z + min_embed.
    """
    fill = sum(s * s for s in scales) / len(scales)
    raw = [target_volume / (w * d * fill) for w, d in footprints]
    bridge_top = bridge_z + bridge_thick
    k = max(1.0, (bridge_top + pierce_margin) / max(raw), (bridge_z + min_embed) / min(raw))
    return [k * h for h in raw], k


def tower_ring(footprints: list[tuple[float, float]], spacing_mult: float) -> tuple[list[tuple[float, float, float]], float, float]:
    """
    Towers on a circle, each facing the centre (local Y = outward). The inner
    faces are spaced spacing_mult * widest tower apart, which sets the radius.
    Returns ([(cx, cy, theta), ...], ring_radius, pitch).
    """
    n = len(footprints)
    pitch = spacing_mult * max(w for w, _ in footprints)
    radius = pitch / (2.0 * math.sin(math.pi / n)) + max(d for _, d in footprints) / 2.0
    centers = []
    for i in range(n):
        a = math.pi / 2.0 + 2.0 * math.pi * i / n  # tower 0 on +Y
        centers.append((radius * math.cos(a), radius * math.sin(a), a - math.pi / 2.0))
    return centers, radius, pitch


def tower_module_specs(i: int, cx: float, cy: float, theta: float, w: float, d: float, h: float,
                       scales: list[float] = None, overlap: float = OVERLAP) -> list[tuple]:
    """
    Stepped shaft (one box per tier, each sunk `overlap` into the one below)
    plus one accent chosen by i % 3, all in the tower's rotated frame
    (u = along the ring, v = outward). Every accent overlaps the shaft.
    """
    if scales is None:
        scales = tier_scales()
    c, s = math.cos(theta), math.sin(theta)

    def box(u0, v0, u1, v1, z0, z1):
        um, vm = (u0 + u1) / 2.0, (v0 + v1) / 2.0
        return ("box", (cx + um * c - vm * s, cy + um * s + vm * c, theta, u1 - u0, v1 - v0, z0, z1))

    dz = h / len(scales)
    specs = [
        box(-f * w / 2.0, -f * d / 2.0, f * w / 2.0, f * d / 2.0, 0.0 if j == 0 else j * dz - overlap, (j + 1) * dz)
        for j, f in enumerate(scales)
    ]
    tw, td = scales[-1] * w, scales[-1] * d
    kind = i % 3
    if kind == 0:
        # cantilevered block at 55-68 % height, rooted in the top tier, pushing outward
        specs.append(box(-0.4 * w, td / 2.0 - overlap, 0.4 * w, d / 2.0 + 0.4 * d, 0.55 * h, 0.68 * h))
    elif kind == 1:
        # drum on top of the slim top tier, sunk `overlap` into it
        specs.append(("cyl", (cx, cy, h - overlap, 0.4 * min(tw, td) + overlap, 0.35 * min(tw, td))))
    else:
        # wide low plinth + thin tall fin on the base tier's +u side
        specs.append(box(-0.75 * w, -0.75 * d, 0.75 * w, 0.75 * d, 0.0, max(overlap, 0.08 * h)))
        specs.append(box(w / 2.0 - overlap, -0.3 * d, w / 2.0 + 0.1 * w, 0.3 * d, 0.0, 1.1 * h))
    return specs


def lintel_specs(centers: list[tuple[float, float, float]], bridge_z: float, bridge_thick: float,
                 cantilever_len: float, depth: float = LINTEL_DEPTH) -> list[tuple]:
    """
    One lintel per pair of neighbouring towers, running centre to centre plus
    cantilever_len past each end, so the beams rest on and cross above towers.
    """
    n = len(centers)
    specs = []
    for i in range(n):
        x0, y0, _ = centers[i]
        x1, y1, _ = centers[(i + 1) % n]
        length = math.hypot(x1 - x0, y1 - y0) + 2.0 * cantilever_len
        specs.append(("box", ((x0 + x1) / 2.0, (y0 + y1) / 2.0, math.atan2(y1 - y0, x1 - x0),
                              length, depth, bridge_z, bridge_z + bridge_thick)))
    return specs


def spec_bounds(spec: tuple) -> tuple[float, float, float, float, float, float]:
    """World axis-aligned bounds (x0, y0, z0, x1, y1, z1) of a part spec."""
    kind, p = spec
    if kind == "cyl":
        xc, yc, z0, height, r = p
        return (xc - r, yc - r, z0, xc + r, yc + r, z0 + height)
    cx, cy, theta, sx, sy, z0, z1 = p
    c, s = math.cos(theta), math.sin(theta)
    xs = [cx + u * c - v * s for u in (-sx / 2.0, sx / 2.0) for v in (-sy / 2.0, sy / 2.0)]
    ys = [cy + u * s + v * c for u in (-sx / 2.0, sx / 2.0) for v in (-sy / 2.0, sy / 2.0)]
    return (min(xs), min(ys), z0, max(xs), max(ys), z1)


def composition_extents(specs: list[tuple]) -> dict:
    """
    Plan extents of ALL parts (shafts, accents, lintels), so the arch always
    follows the real geometry rather than the bare shafts.
    """
    bounds = [spec_bounds(s) for s in specs]
    return {
        "x_min": min(b[0] for b in bounds),
        "x_max": max(b[3] for b in bounds),
        "y_min": min(b[1] for b in bounds),
        "y_max": max(b[4] for b in bounds),
    }


def _guard(value, default, minimum=None, cast=float):
    """None -> default, otherwise cast and clamp to `minimum`."""
    if value is None:
        return default
    value = cast(value)
    return value if minimum is None else max(minimum, value)


def _design_constants(overrides: dict) -> dict:
    """Module-level design constants, updated by **overrides (unknown keys raise)."""
    c = {
        "BASE_W": BASE_W, "BASE_D": BASE_D, "TARGET_VOLUME": TARGET_VOLUME,
        "BRIDGE_THICK": BRIDGE_THICK, "PIERCE_MARGIN": PIERCE_MARGIN,
        "CYL_OVERSHOOT": CYL_OVERSHOOT, "W_FACTORS": W_FACTORS,
        "D_FACTORS": D_FACTORS, "TIERS": TIERS, "TOP_SCALE": TOP_SCALE,
        "LINTEL_DEPTH": LINTEL_DEPTH, "OVERLAP": OVERLAP,
    }
    unknown = set(overrides) - set(c)
    if unknown:
        raise TypeError("Unknown design constant(s): " + ", ".join(sorted(unknown)))
    c.update(overrides)
    return c


def composition_layout(
    tower_count: int = 3,
    spacing_mult: float = 2.5,
    bridge_z: float = 100.0,
    cantilever_len: float = 20.0,
    cylinder_radius: float = 10.0,
    cylinder_z_center: float = 0.0,
    **overrides,
) -> dict:
    """
    Whole composition as plain numbers: tower and lintel specs, arch
    parameters and info. The arch is centred on the FINAL extents.
    """
    c = _design_constants(overrides)
    n = _guard(tower_count, 3, 3, int)
    spacing_mult = _guard(spacing_mult, 2.5, 1.05)
    bridge_z = _guard(bridge_z, 100.0, 1.0)
    cantilever_len = _guard(cantilever_len, 20.0, 0.0)
    cylinder_radius = _guard(cylinder_radius, 10.0, 0.1)
    cylinder_z_center = _guard(cylinder_z_center, 0.0)

    scales = tier_scales(c["TIERS"], c["TOP_SCALE"])
    footprints = tower_footprints(n, c["BASE_W"], c["BASE_D"], c["W_FACTORS"], c["D_FACTORS"])
    heights, k = tower_heights(footprints, c["TARGET_VOLUME"], bridge_z, c["BRIDGE_THICK"],
                               c["PIERCE_MARGIN"], c["OVERLAP"], scales)
    centers, ring_radius, pitch = tower_ring(footprints, spacing_mult)
    towers = [
        tower_module_specs(i, cx, cy, theta, w, d, h, scales, c["OVERLAP"])
        for i, ((cx, cy, theta), (w, d), h) in enumerate(zip(centers, footprints, heights))
    ]
    lintels = lintel_specs(centers, bridge_z, c["BRIDGE_THICK"], cantilever_len, c["LINTEL_DEPTH"])

    ext = composition_extents([s for t in towers for s in t] + lintels)
    bridge_top = bridge_z + c["BRIDGE_THICK"]
    return {
        "footprints": footprints,
        "scales": scales,
        "centers": centers,
        "towers": towers,
        "lintels": lintels,
        "arch": ((ext["x_min"] + ext["x_max"]) / 2.0, ext["y_min"], ext["y_max"],
                 cylinder_radius, cylinder_z_center, c["CYL_OVERSHOOT"]),
        "info": {
            "pitch": pitch,
            "ring_radius": ring_radius,
            "k": k,
            "heights": heights,
            "bridge_x0": ext["x_min"],
            "bridge_x1": ext["x_max"],
            "bridge_top": bridge_top,
            "pierce_amount": max(heights) - bridge_top,
        },
    }


# --- B) Rhino geometry (Rhino.Geometry only, nothing added to the document) ---

def box_brep(x0: float, y0: float, z0: float, x1: float, y1: float, z1: float) -> "rg.Brep":
    """Closed axis-aligned box Brep between two corner points."""
    return rg.BoundingBox(rg.Point3d(x0, y0, z0), rg.Point3d(x1, y1, z1)).ToBrep()


def oriented_box_brep(cx: float, cy: float, theta: float, sx: float, sy: float,
                      z0: float, z1: float) -> "rg.Brep":
    """Closed box centred on (cx, cy) in plan, rotated by theta about Z, from z0 to z1."""
    plane = rg.Plane(rg.Point3d(cx, cy, z0),
                     rg.Vector3d(math.cos(theta), math.sin(theta), 0),
                     rg.Vector3d(-math.sin(theta), math.cos(theta), 0))
    box = rg.Box(plane, rg.Interval(-sx / 2.0, sx / 2.0), rg.Interval(-sy / 2.0, sy / 2.0),
                 rg.Interval(0, z1 - z0))
    return box.ToBrep()


def cylinder_brep_vertical(xc: float, yc: float, z0: float, height: float, radius: float) -> "rg.Brep":
    """Capped vertical cylinder standing on (xc, yc, z0)."""
    circle = rg.Circle(rg.Plane(rg.Point3d(xc, yc, z0), rg.Vector3d.ZAxis), radius)
    return rg.Cylinder(circle, height).ToBrep(True, True)


def _spec_to_brep(spec: tuple) -> "rg.Brep":
    kind, p = spec
    return oriented_box_brep(*p) if kind == "box" else cylinder_brep_vertical(*p)


def tower_modules(i: int, cx: float, cy: float, theta: float, w: float, d: float, h: float) -> list["rg.Brep"]:
    """
    Breps for one tower: stepped, slimming shaft plus the accent picked by
    i % 3 (0 cantilever, 1 drum, 2 plinth + fin), each overlapping the shaft.
    """
    return [_spec_to_brep(s) for s in tower_module_specs(i, cx, cy, theta, w, d, h)]


def make_bridge(centers: list[tuple[float, float, float]], bridge_z: float, bridge_thick: float,
                cantilever_len: float, depth: float = LINTEL_DEPTH) -> list["rg.Brep"]:
    """
    Ring of lintel boxes, one per neighbouring pair of towers, each running
    cantilever_len past both towers (Stonehenge trilithons on a sky bridge).
    """
    return [_spec_to_brep(s) for s in lintel_specs(centers, bridge_z, bridge_thick, cantilever_len, depth)]


def make_arch_void(x_mid: float, y_min: float, y_max: float, radius: float,
                   z_center: float, overshoot: float = 2.0) -> "rg.Brep":
    """
    Capped cylinder along Y through the whole depth (+ overshoot each side),
    used as the cutter for a Solid Difference in Grasshopper.
    """
    start = rg.Point3d(x_mid, y_min - overshoot, z_center)
    circle = rg.Circle(rg.Plane(start, rg.Vector3d.YAxis), radius)
    return rg.Cylinder(circle, (y_max - y_min) + 2.0 * overshoot).ToBrep(True, True)


def build_composition(
    tower_count: int = 3,
    spacing_mult: float = 2.5,
    bridge_z: float = 100.0,
    cantilever_len: float = 20.0,
    cylinder_radius: float = 10.0,
    cylinder_z_center: float = 0.0,
    **overrides,
) -> dict:
    """
    Converts composition_layout(...) into Breps:
    {"towers": [Brep, ...], "bridge": [Brep, ...], "arch_void": Brep, "info": {...}}.
    """
    layout = composition_layout(tower_count, spacing_mult, bridge_z, cantilever_len,
                                cylinder_radius, cylinder_z_center, **overrides)
    return {
        "towers": [_spec_to_brep(s) for tower in layout["towers"] for s in tower],
        "bridge": [_spec_to_brep(s) for s in layout["lintels"]],
        "arch_void": make_arch_void(*layout["arch"]),
        "info": layout["info"],
    }
