"""
Assignment 1 -- Munich Bauhaus Stonehenge -- 05 PLINTH

Inputs
    List Access: widths, depths  <- 01 Layout
    Item Access: radius          <- 01 Layout
Outputs: geometry, colors   (geometry -> Custom Preview G, colors -> M)

Relationships
    (radius) -> PLINTH radius = ring radius + half the largest tower diagonal
                + PLINTH_MARGIN, so the base always holds the whole ring.
"""

import importlib
import math
import Rhino.Geometry as rg
from System.Drawing import Color
import cdf.geometry_basics as gb
importlib.reload(gb)

PLINTH_THICK, PLINTH_MARGIN = 2.0, 15.0

plinth_radius = radius + max(math.hypot(w, d) for w, d in zip(widths, depths)) / 2.0 + PLINTH_MARGIN
geometry = gb.create_cylinder(rg.Point3d(0, 0, -PLINTH_THICK), plinth_radius, PLINTH_THICK)
colors = Color.FromArgb(235, 235, 230)
