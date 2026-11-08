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


def unwrap(values, cast=None):
    """
    Turn Grasshopper input values into plain Python values.

    values : a list (List Access input) or a single value (Item Access)
    cast   : optional type to convert each value to, e.g. float

    Grasshopper can hand Python wrapped values (GH_Number, GH_Point, ...)
    when an input has no type hint; their real value sits in `.Value`.
    Returns a list if `values` is a list, otherwise a single value.
    """
    def one(v):
        v = getattr(v, "Value", v)
        return cast(v) if cast is not None else v

    if isinstance(values, (list, tuple)) or hasattr(values, "Count"):
        return [one(v) for v in values]
    return one(values)


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


def boolean_union(breps, tolerance=0.001):
    """
    Join overlapping Breps into as few solids as possible.

    breps     : list of Rhino.Geometry.Brep -- the solids to join
    tolerance : float -- boolean tolerance

    Returns a list of Rhino.Geometry.Brep; the inputs unchanged if the union fails.
    """
    breps = [b for b in breps if b is not None]
    if len(breps) < 2:
        return breps
    result = rg.Brep.CreateBooleanUnion(breps, tolerance)
    return list(result) if result else breps


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


def create_box(base_point=None, width=10.0, depth=10.0, height=10.0, angle=0.0):
    """
    Build a closed box standing on the XY plane, rotated about Z.

    base_point : Rhino.Geometry.Point3d -- centre of the box's bottom face
    width      : float -- size along the box's local X
    depth      : float -- size along the box's local Y
    height     : float -- size along Z
    angle      : float -- rotation about Z in radians

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)

    x_axis = rg.Vector3d(math.cos(angle), math.sin(angle), 0)
    y_axis = rg.Vector3d(-math.sin(angle), math.cos(angle), 0)
    plane = rg.Plane(base_point, x_axis, y_axis)
    box = rg.Box(plane, rg.Interval(-width / 2.0, width / 2.0),
                 rg.Interval(-depth / 2.0, depth / 2.0), rg.Interval(0, height))
    return box.ToBrep()


def create_cylinder(base_point=None, radius=5.0, height=10.0, direction=None):
    """
    Build a capped cylinder.

    base_point : Rhino.Geometry.Point3d -- centre of the start circle
    radius     : float -- circle radius
    height     : float -- length along `direction`
    direction  : Rhino.Geometry.Vector3d -- cylinder axis (Z by default)

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    if direction is None:
        direction = rg.Vector3d.ZAxis

    circle = rg.Circle(rg.Plane(base_point, direction), radius)
    return rg.Cylinder(circle, height).ToBrep(True, True)


def create_prism(base_point=None, radius=5.0, sides=3, height=10.0, angle=0.0):
    """
    Build a closed prism on a regular polygon (sides=3 gives a triangle).

    base_point : Rhino.Geometry.Point3d -- centre of the bottom polygon
    radius     : float -- distance from the centre to each corner
    sides      : int   -- number of polygon corners
    height     : float -- extrusion height along Z
    angle      : float -- rotation about Z in radians; one corner points
                          along the rotated local +Y

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)

    sides = max(3, int(sides))
    corners = []
    for k in range(sides + 1):  # repeat the first corner to close the polygon
        a = angle + math.pi / 2.0 + 2.0 * math.pi * k / sides
        corners.append(rg.Point3d(base_point.X + radius * math.cos(a),
                                  base_point.Y + radius * math.sin(a), base_point.Z))
    profile = rg.PolylineCurve(corners)
    surface = rg.Surface.CreateExtrusion(profile, rg.Vector3d(0, 0, height))
    brep = surface.ToBrep()
    brep.Faces.SplitKinkyFaces(math.radians(1.0), True)  # one face per side
    solid = brep.CapPlanarHoles(0.001)
    if solid is None:
        return brep
    if solid.SolidOrientation == rg.BrepSolidOrientation.Inward:
        solid.Flip()  # normals must point outward for booleans
    return solid


def create_beam(start, end, width=1.0, thickness=1.0):
    """
    Build a box whose bottom face runs from `start` to `end`, so it can
    rest on two supports at different heights.

    start, end : Rhino.Geometry.Point3d -- ends of the bottom centre line
    width      : float -- horizontal size across the beam
    thickness  : float -- size perpendicular to the beam, upward

    Returns a Rhino.Geometry.Brep.
    """
    x_axis = end - start
    length = x_axis.Length
    y_axis = rg.Vector3d.CrossProduct(rg.Vector3d.ZAxis, x_axis)  # horizontal, across
    plane = rg.Plane(start, x_axis, y_axis)
    box = rg.Box(plane, rg.Interval(0, length), rg.Interval(-width / 2.0, width / 2.0),
                 rg.Interval(0, thickness))
    return box.ToBrep()


def create_stepped_tower(base_point=None, width=10.0, depth=10.0, height=30.0,
                         tiers=3, top_scale=0.6, angle=0.0, overlap=1.0, align=0.0,
                         shape="box"):
    """
    Build a tower of stacked blocks that get slimmer toward the top.

    base_point : Rhino.Geometry.Point3d -- centre of the tower's footprint
    width      : float -- bottom tier size along local X
    depth      : float -- bottom tier size along local Y
    height     : float -- total tower height
    tiers      : int   -- number of stacked blocks
    top_scale  : float -- top tier size as a fraction of the bottom tier
    angle      : float -- rotation about Z in radians
    overlap    : float -- how far each tier sinks into the one below, so a
                          Solid Union never meets two faces lying exactly flush
    align      : float -- where the setbacks go along local Y: 0 centres every
                          tier, -1 / +1 pushes them to the -Y / +Y side
    shape      : str   -- "box", "cylinder" or "triangle"; round and
                          triangular blocks use radius (width + depth) / 4

    Returns a list of Rhino.Geometry.Brep, one per tier.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)

    tiers = max(1, int(tiers))
    tier_height = height / tiers
    radius = (width + depth) / 4.0
    blocks = []
    for j in range(tiers):
        scale = 1.0 if tiers == 1 else 1.0 - j * (1.0 - top_scale) / (tiers - 1)
        z0 = 0.0 if j == 0 else j * tier_height - overlap
        h = (j + 1) * tier_height - z0
        shift = align * (1.0 - scale) * depth / 2.0  # slide along local Y
        p = rg.Point3d(base_point.X - shift * math.sin(angle),
                       base_point.Y + shift * math.cos(angle), base_point.Z + z0)
        if shape == "cylinder":
            blocks.append(create_cylinder(p, radius * scale, h))
        elif shape == "triangle":
            blocks.append(create_prism(p, radius * scale, 3, h, angle))
        else:
            blocks.append(create_box(p, width * scale, depth * scale, h, angle))
    return blocks
