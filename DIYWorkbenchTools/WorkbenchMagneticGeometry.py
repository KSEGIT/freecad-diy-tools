"""Pure world-space geometry helpers for Magnetic Move.

Candidates are ``(kind, App.Vector world_point, label)`` tuples. Shapes must
already include their world placement, as independent document shapes do.
These helpers never modify the shape, placement, or vectors supplied to them.
"""
import FreeCAD as App
import Part


_AXIS_COMPONENT = {'X': 'x', 'Y': 'y', 'Z': 'z'}
_AXIS_EPSILON = 1e-6
_PRIORITY = {'vertex': 0, 'midpoint': 1, 'face': 2}


def shape_candidates(shape, label):
    """Return a list of real vertices and straight-edge midpoint candidates.

    Curved edges do not contribute midpoint candidates. Planar face candidates
    are supplied separately by the view's surface picking logic.
    """
    candidates = [
        ('vertex', App.Vector(vertex.Point), '{} · Vertex {}'.format(label, index))
        for index, vertex in enumerate(shape.Vertexes, 1)
    ]
    for index, edge in enumerate(shape.Edges, 1):
        if isinstance(edge.Curve, (Part.Line, Part.LineSegment)):
            parameter = (edge.FirstParameter + edge.LastParameter) / 2.0
            candidates.append(('midpoint', edge.valueAt(parameter),
                               '{} · Edge {} midpoint'.format(label, index)))
    return candidates


def constrained_point(point, anchor, axis=None):
    """Return a new Vector constrained to a world axis through anchor.

    With no axis lock, return an independent copy of point.
    """
    if axis is None:
        return App.Vector(point)
    component = _AXIS_COMPONENT[axis]
    result = App.Vector(anchor)
    setattr(result, component, getattr(point, component))
    return result


def choose_snap(candidates, cursor, project, tolerance=14, anchor=None, axis=None):
    """Return the best candidate within the pixel radius, or None.

    ``project(world_point)`` must return the view's ``(x, y)`` pixel position.
    Prefer vertices, then midpoints, then face points; choose the closest pixel
    position within a kind. Reject locked-axis conflicts before projection.
    """
    if axis is not None and anchor is None:
        raise ValueError('An axis lock requires an anchor')
    best = None
    best_key = None
    radius_squared = tolerance * tolerance
    for candidate in candidates:
        kind, point, _label = candidate
        if axis is not None:
            constrained = constrained_point(point, anchor, axis)
            if (point - constrained).Length > _AXIS_EPSILON:
                continue
        x, y = project(point)
        distance_squared = (x - cursor[0])**2 + (y - cursor[1])**2
        if distance_squared > radius_squared:
            continue
        key = (_PRIORITY[kind], distance_squared)
        if best_key is None or key < best_key:
            best, best_key = candidate, key
    return best


def translated_placement(original, anchor, destination):
    """Return a new Placement translated between world points, without rotation."""
    result = App.Placement(original)
    result.Base = original.Base + (destination - anchor)
    return result
