"""Native geometry regression checks; run with the FreeCAD bundled Python."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'DIYWorkbenchTools'))
import FreeCAD as App
import Part
# FreeCAD prepends installed Mod paths during import. Verify this checkout.
source = Path(__file__).resolve().parents[1] / 'DIYWorkbenchTools'
sys.path.insert(0, str(source))
try:
    import WorkbenchMagneticGeometry as geometry
    assert Path(geometry.__file__).resolve().parent == source.resolve()
except ModuleNotFoundError:
    geometry = None


class MagneticGeometryTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(geometry, 'Magnetic geometry helpers are not implemented')

    def same(self, actual, expected):
        self.assertLess((actual - App.Vector(*expected)).Length, 1e-7)

    def test_rotated_shape_returns_world_vertices_and_straight_midpoints(self):
        shape = Part.makeBox(10, 20, 30)
        shape.Placement = App.Placement(App.Vector(100, 200, 300),
                                        App.Rotation(App.Vector(0, 0, 1), 90))
        before = shape.Placement
        candidates = geometry.shape_candidates(shape, 'Beam')
        vertices = [p for kind, p, label in candidates if kind == 'vertex']
        midpoints = [p for kind, p, label in candidates if kind == 'midpoint']
        self.assertEqual(len(vertices), 8)
        self.assertEqual(len(midpoints), 12)
        self.assertTrue(any((p - App.Vector(80, 210, 330)).Length < 1e-7 for p in vertices))
        self.assertTrue(any((p - App.Vector(100, 205, 300)).Length < 1e-7 for p in midpoints))
        self.assertTrue(all('Beam' in label for _, _, label in candidates))
        self.assertEqual(shape.Placement, before)

    def test_curved_edges_do_not_supply_midpoints(self):
        shape = Part.makeCylinder(5, 10)
        candidates = geometry.shape_candidates(shape, 'Round')
        midpoints = [p for kind, p, _ in candidates if kind == 'midpoint']
        self.assertEqual(len(midpoints), 1)  # Only the straight seam.
        self.same(midpoints[0], (5, 0, 5))

    def test_pixel_tolerance_tracks_projection_and_radial_boundary(self):
        candidate = ('vertex', App.Vector(10, 0, 0), 'Corner')
        self.assertIs(geometry.choose_snap([candidate], (0, 0), lambda p: (p.x, p.y)), candidate)
        self.assertIsNone(geometry.choose_snap([candidate], (0, 0), lambda p: (2*p.x, 2*p.y)))
        self.assertIs(geometry.choose_snap([candidate], (24, 0), lambda p: (p.x, p.y)), candidate)
        self.assertIsNone(geometry.choose_snap([candidate], (24.001, 0), lambda p: (p.x, p.y)))
        self.assertIsNone(geometry.choose_snap([candidate], (20, 10), lambda p: (p.x, p.y)))

    def test_corner_then_midpoint_then_face_priority_and_nearest_tie(self):
        face = ('face', App.Vector(0, 0, 0), 'Face')
        midpoint = ('midpoint', App.Vector(2, 0, 0), 'Edge')
        vertex = ('vertex', App.Vector(13, 0, 0), 'Corner')
        nearer = ('vertex', App.Vector(9, 0, 0), 'Near corner')
        project = lambda p: (p.x, p.y)
        self.assertIs(geometry.choose_snap([face, midpoint, vertex], (0, 0), project), vertex)
        self.assertIs(geometry.choose_snap([face, midpoint], (0, 0), project), midpoint)
        self.assertIs(geometry.choose_snap([face], (0, 0), project), face)
        self.assertIs(geometry.choose_snap([vertex, nearer], (0, 0), project), nearer)
        self.assertIsNone(geometry.choose_snap([], (0, 0), project))

    def test_axis_rejects_incompatible_targets_before_projection(self):
        anchor = App.Vector(10, 20, 30)
        for axis, good, bad in [('X', (50,20,30), (50,20,31)),
                                ('Y', (10,50,30), (11,50,30)),
                                ('Z', (10,20,50), (10,21,50))]:
            compatible = ('midpoint', App.Vector(*good), 'Valid')
            incompatible = ('vertex', App.Vector(*bad), 'Invalid')
            projected = []
            def project(point):
                projected.append(point)
                return (0, 0)
            chosen = geometry.choose_snap([incompatible, compatible], (0,0), project,
                                          anchor=anchor, axis=axis)
            self.assertIs(chosen, compatible)
            self.assertEqual(projected, [compatible[1]])
        drift = ('vertex', App.Vector(50,20 + 1e-8,30), 'Roundoff')
        self.assertIs(geometry.choose_snap([drift], (0,0), lambda p:(0,0),
                                          anchor=anchor, axis='X'), drift)

    def test_constraints_keep_anchor_coordinates_and_leave_inputs_intact(self):
        point = App.Vector(1, 2, 3)
        anchor = App.Vector(10, 20, 30)
        for axis, expected in [(None, (1,2,3)), ('X',(1,20,30)),
                               ('Y',(10,2,30)), ('Z',(10,20,3))]:
            self.same(geometry.constrained_point(point, anchor, axis), expected)
        self.same(point, (1,2,3))
        self.same(anchor, (10,20,30))

    def test_translation_preserves_exact_rotation_and_original_placement(self):
        original = App.Placement(App.Vector(10,20,30), App.Rotation(App.Vector(1,2,3), 37))
        rotation = original.Rotation.Q
        local_corner = App.Vector(4,5,6)
        anchor = original.multVec(local_corner)
        destination = anchor + App.Vector(-40,50,7)
        translated = geometry.translated_placement(original, anchor, destination)
        self.same(translated.Base, (-30,70,37))
        self.assertEqual(translated.Rotation.Q, rotation)
        self.assertLess((translated.multVec(local_corner) - destination).Length, 1e-7)
        self.same(original.Base, (10,20,30))
        self.assertEqual(original.Rotation.Q, rotation)


if __name__ == '__main__':
    unittest.main(verbosity=2)
