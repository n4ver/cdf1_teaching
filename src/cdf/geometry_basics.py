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

BASE_W = 40.0
BASE_D = 30.0
TARGET_VOLUME = 60000.0
BRIDGE_THICK = 8.0
PIERCE_MARGIN = 15.0
CYL_OVERSHOOT = 2.0
W_FACTORS = [1.00, 1.35, 0.70]
D_FACTORS = [1.00, 0.70, 1.25, 0.90]

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

def create_sphere():
    pass  # TODO: Implement this function to create a sphere using Rhino.Geometry

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


def box_from_bounds(
    x0: float, y0: float, z0: float, x1: float, y1: float, z1: float
) -> rg.Brep:
    """Create a closed axis-aligned Brep from two opposite corners."""
    bounds = rg.BoundingBox(rg.Point3d(x0, y0, z0), rg.Point3d(x1, y1, z1))
    return rg.Box(bounds).ToBrep()


def tower_footprints(
    n: int,
    base_w: float,
    base_d: float,
    w_factors: list[float],
    d_factors: list[float],
) -> list[tuple[float, float]]:
    """Return tower width/depth pairs using independently cycled factors."""
    if n < 1:
        raise ValueError("n must be at least 1.")
    if not w_factors or not d_factors:
        raise ValueError("w_factors and d_factors must not be empty.")
    return [
        (base_w * w_factors[i % len(w_factors)],
         base_d * d_factors[i % len(d_factors)])
        for i in range(n)
    ]


def tower_heights(
    footprints: list[tuple[float, float]],
    target_volume: float,
    bridge_z: float,
    bridge_thick: float,
    pierce_margin: float,
) -> tuple[list[float], float]:
    """Scale constant-volume tower heights to satisfy both bridge constraints."""
    if not footprints:
        raise ValueError("footprints must not be empty.")
    raw_heights = [target_volume / (w * d) for w, d in footprints]
    bridge_top = bridge_z + bridge_thick
    k = max(
        1.0,
        (bridge_top + pierce_margin) / max(raw_heights),
        bridge_z / min(raw_heights),
    )
    return [height * k for height in raw_heights], k


def tower_x_centers(
    footprints: list[tuple[float, float]], spacing_mult: float
) -> list[float]:
    """Return evenly pitched tower centers centered on the world X origin."""
    if not footprints:
        raise ValueError("footprints must not be empty.")
    pitch = spacing_mult * max(w for w, _ in footprints)
    return [(i - (len(footprints) - 1) / 2.0) * pitch
            for i in range(len(footprints))]


def make_towers(
    footprints: list[tuple[float, float]],
    heights: list[float],
    x_centers: list[float],
) -> list[rg.Brep]:
    """Create closed tower Breps from footprints, heights, and X centers."""
    if not (len(footprints) == len(heights) == len(x_centers)):
        raise ValueError("footprints, heights, and x_centers must have equal lengths.")
    return [
        box_from_bounds(
            xc - w / 2.0, -d / 2.0, 0.0,
            xc + w / 2.0, d / 2.0, height,
        )
        for (w, d), height, xc in zip(footprints, heights, x_centers)
    ]


def make_bridge(
    footprints: list[tuple[float, float]],
    x_centers: list[float],
    bridge_z: float,
    bridge_thick: float,
    cantilever_len: float,
) -> rg.Brep:
    """Create the bridge slab spanning the towers and both cantilevers."""
    if not footprints or len(footprints) != len(x_centers):
        raise ValueError("footprints and x_centers must have equal non-zero lengths.")
    x_min = min(xc - w / 2.0 for (w, _), xc in zip(footprints, x_centers))
    x_max = max(xc + w / 2.0 for (w, _), xc in zip(footprints, x_centers))
    y_max = max(d for _, d in footprints) / 2.0
    return box_from_bounds(
        x_min - cantilever_len, -y_max, bridge_z,
        x_max + cantilever_len, y_max, bridge_z + bridge_thick,
    )


def make_arch_void(
    bridge_x0: float,
    bridge_x1: float,
    y_min: float,
    y_max: float,
    radius: float,
    z_center: float,
    overshoot: float,
) -> rg.Brep:
    """Create a capped cylinder along +Y for use as a bridge subtraction void."""
    x_mid = (bridge_x0 + bridge_x1) / 2.0
    y_start = y_min - overshoot
    plane = rg.Plane(
        rg.Point3d(x_mid, y_start, z_center), rg.Vector3d.YAxis
    )
    cylinder = rg.Cylinder(
        rg.Circle(plane, radius),
        (y_max - y_min) + 2.0 * overshoot,
    )
    return cylinder.ToBrep(True, True)


def build_composition(
    tower_count: int,
    spacing_mult: float,
    bridge_z: float,
    cantilever_len: float,
    cylinder_radius: float,
    cylinder_z_center: float,
    **constants: object,
) -> dict[str, object]:
    """Build the complete tower, bridge, and arch-void composition."""
    n = max(1, int(tower_count if tower_count is not None else 3))
    s_mult = max(1.05, float(spacing_mult if spacing_mult is not None else 1.6))
    b_z = max(1.0, float(bridge_z if bridge_z is not None else 120.0))
    cant = max(0.0, float(cantilever_len if cantilever_len is not None else 40.0))
    cyl_r = max(0.1, float(cylinder_radius if cylinder_radius is not None else 35.0))
    cyl_zc = float(cylinder_z_center if cylinder_z_center is not None else 0.0)

    def constant(name, default):
        return constants.get(name, constants.get(name.upper(), default))

    base_w = float(constant("base_w", BASE_W))
    base_d = float(constant("base_d", BASE_D))
    target_volume = float(constant("target_volume", TARGET_VOLUME))
    bridge_thick = float(constant("bridge_thick", BRIDGE_THICK))
    pierce_margin = float(constant("pierce_margin", PIERCE_MARGIN))
    cyl_overshoot = float(constant("cyl_overshoot", CYL_OVERSHOOT))
    w_factors = constant("w_factors", W_FACTORS)
    d_factors = constant("d_factors", D_FACTORS)

    footprints = tower_footprints(n, base_w, base_d, w_factors, d_factors)
    heights, k = tower_heights(
        footprints, target_volume, b_z, bridge_thick, pierce_margin
    )
    x_centers = tower_x_centers(footprints, s_mult)
    towers = make_towers(footprints, heights, x_centers)

    x_min = min(xc - w / 2.0 for (w, _), xc in zip(footprints, x_centers))
    x_max = max(xc + w / 2.0 for (w, _), xc in zip(footprints, x_centers))
    y_min = -max(d for _, d in footprints) / 2.0
    y_max = -y_min
    bridge_x0 = x_min - cant
    bridge_x1 = x_max + cant
    bridge_top = b_z + bridge_thick
    bridge = make_bridge(
        footprints, x_centers, b_z, bridge_thick, cant
    )
    arch_void = make_arch_void(
        bridge_x0, bridge_x1, y_min, y_max, cyl_r, cyl_zc, cyl_overshoot
    )

    info = {
        "pitch": s_mult * max(w for w, _ in footprints),
        "effective_volume": target_volume * k,
        "k": k,
        "heights": heights,
        "bridge_x0": bridge_x0,
        "bridge_x1": bridge_x1,
        "bridge_top": bridge_top,
        "pierce_amount": max(heights) - bridge_top,
        "footprints": footprints,
        "x_centers": x_centers,
    }
    return {
        "towers": towers,
        "bridge": bridge,
        "arch_void": arch_void,
        "info": info,
    }