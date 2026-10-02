"""Whole-part connection checks using native FreeCAD solids."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'DIYWorkbenchTools'))
import FreeCAD as App
import Part
# FreeCAD initialization prepends installed add-ons; test this checkout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'DIYWorkbenchTools'))
try:
    from WorkbenchConnectionSnap import connection_snap
except ModuleNotFoundError:
    connection_snap = None


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(connection_snap, 'Whole-part connection inference is missing')
        self.source = Part.makeBox(1700, 94, 44)
        self.target = Part.makeBox(1700, 94, 44)

    def snap(self, raw, source=None, targets=None, **kw):
        return connection_snap(source or self.source, targets or [('Beam', self.target)],
                               App.Vector(*raw), lambda p:(p.x, p.y + p.z), **kw)

    def vector(self, actual, expected):
        self.assertLess((actual - App.Vector(*expected)).Length, 1e-6)

    def test_end_extension_flushes_width_and_thickness(self):
        result = self.snap((1710, 5, 3))
        self.assertIsNotNone(result)
        self.vector(result['delta'], (1700, 0, 0))
        self.assertEqual(result['kind'], 'extension')
        self.vector(result['source'] + result['delta'], tuple(result['target']))

    def test_upright_butt_flushes_face_corners(self):
        upright = Part.makeBox(94, 94, 1700)
        result = self.snap((100, 5, 3), targets=[('Upright', upright)])
        self.assertIsNotNone(result)
        self.vector(result['delta'], (94, 0, 0))

    def test_side_and_stacked_contacts_keep_in_plane_position(self):
        for raw, expected in [((200, 100, 4),(200,94,4)),
                              ((200, 30, 49),(200,30,44))]:
            result = self.snap(raw)
            self.assertIsNotNone(result)
            self.vector(result['delta'], expected)

    def test_wrong_corner_overlap_cannot_be_selected(self):
        blocker = Part.makeBox(100,94,44,App.Vector(1750,0,0))
        result = self.snap((1710,5,3), targets=[('Beam',self.target),('Blocker',blocker)])
        self.assertIsNone(result, 'Every nearby joint embeds the rail in the blocker')

    def test_free_away_releases_and_depth_projection_does_not_teleport(self):
        self.assertIsNone(self.snap((2000,300,300)))
        self.assertIsNone(connection_snap(self.source,[('Beam',self.target)],
            App.Vector(1710,0,500),lambda p:(p.x,p.y)))

    def test_pixel_capture_changes_with_zoom(self):
        self.assertIsNone(connection_snap(self.source,[('Beam',self.target)],
            App.Vector(1720,0,0),lambda p:(p.x*2,p.y*2)))
        self.assertIsNotNone(connection_snap(self.source,[('Beam',self.target)],
            App.Vector(1720,0,0),lambda p:(p.x*.5,p.y*.5)))

    def test_matching_end_profile_infers_flush_extension_despite_lateral_drift(self):
        result = connection_snap(self.source, [("Beam",self.target)],
            App.Vector(1702,10,10),lambda p:(p.x,p.y))
        self.assertIsNotNone(result)
        self.vector(result["delta"], (1700,0,0))

    def test_near_other_joint_beats_farther_end_extension(self):
        side = Part.makeBox(1700,94,44,App.Vector(1800,105,10))
        result = connection_snap(self.source, [("NearSide",side),("EndBeam",self.target)],
            App.Vector(1702,10,10),lambda p:(p.x,p.y))
        self.assertIsNotNone(result)
        self.vector(result["delta"], (1702,11,10))
        self.assertEqual(result["label"], "NearSide")

    def test_blocked_extension_releases_safe_partial_face_contact(self):
        blocker = Part.makeBox(2,2,2,App.Vector(1750,0,0))
        result = self.snap((1710,5,3), targets=[("Beam",self.target),("Blocker",blocker)])
        self.assertIsNotNone(result)
        self.vector(result["delta"], (1700,5,3))
        moved = self.source.copy()
        moved.translate(result["delta"])
        self.assertLess(moved.common(blocker).Volume,1e-7)

    def test_axis_correction_obeys_each_lock(self):
        for axis, raw, expected in [('X',(1710,5,3),(1700,5,3)),
                                    ('Y',(200,100,4),(200,94,4)),
                                    ('Z',(200,30,49),(200,30,44))]:
            result=self.snap(raw,axis=axis)
            self.assertIsNotNone(result)
            self.vector(result['delta'],expected)

    def test_rotated_world_shapes_and_inputs_are_unchanged(self):
        rotation=App.Rotation(App.Vector(0,0,1),37)
        placement=App.Placement(App.Vector(80,90,30),rotation)
        self.source.Placement=placement
        self.target.Placement=placement
        source_before = self.source.Placement
        target_before = self.target.Placement
        raw=rotation.multVec(App.Vector(1710,5,3))
        result=connection_snap(self.source,[('Rotated',self.target)],raw,
                               lambda p:(p.x,p.y+p.z))
        self.assertIsNotNone(result)
        self.assertLess((result['delta']-rotation.multVec(App.Vector(1700,0,0))).Length,1e-6)
        self.assertEqual(self.source.Placement,source_before)
        self.assertEqual(self.target.Placement,target_before)
        self.assertLess((raw-rotation.multVec(App.Vector(1710,5,3))).Length,1e-6)

    def test_previous_connection_stays_near_boundary_then_releases(self):
        previous=self.snap((1710,0,0))
        result=self.snap((1719,0,0),previous=previous)
        self.assertIsNotNone(result)
        self.assertEqual(result['key'],previous['key'])
        self.assertIsNone(self.snap((1730,0,0),previous=previous))


    def depth_case(self, perspective=False, blocker=False, axis=None):
        from pivy import coin
        camera = coin.SoPerspectiveCamera() if perspective else coin.SoOrthographicCamera()
        direction = App.Vector(1, 1, 1); direction.normalize()
        camera.orientation = coin.SbRotation(coin.SbVec3f(0,0,-1), coin.SbVec3f(*tuple(direction)))
        camera.position = coin.SbVec3f(-2000,-2000,-2000)
        if not perspective:
            camera.height = 2000
        volume = camera.getViewVolume(1.5)
        def project(point):
            pixel = volume.projectToScreen(coin.SbVec3f(*tuple(point)))
            return pixel[0]*1500, pixel[1]*1000
        source = Part.makeBox(44,94,900,App.Vector(300,-300,0))
        target = Part.makeBox(1700,94,44)
        desired = App.Vector(0,300,44)
        pixel = project(source.CenterOfMass + desired)
        near, far = volume.projectPointToLine(coin.SbVec2f(pixel[0]/1500,pixel[1]/1000))
        origin = App.Vector(tuple(near)); ray = App.Vector(tuple(far))-origin
        plane = origin + ray*((source.CenterOfMass-origin).dot(direction)/ray.dot(direction))
        raw = plane-source.CenterOfMass
        self.assertGreater((desired-raw).Length, 50)
        top = next(i for i, face in enumerate(target.Faces) if face.normalAt(0,0).z > .99)
        targets = [('Rail',target)]
        if blocker:
            targets.append(('Blocker',Part.makeBox(44,94,100,App.Vector(300,0,44))))
        def local_ray(point):
            px = project(point)
            a,b = volume.projectPointToLine(coin.SbVec2f(px[0]/1500,px[1]/1000))
            return App.Vector(tuple(b))-App.Vector(tuple(a))
        result = connection_snap(source,targets,raw,project,view_direction=local_ray if perspective else direction,
                                 depth_faces={0:{top}},axis=axis)
        return source,target,result,desired

    def test_visible_top_face_resolves_orthographic_depth(self):
        source,target,result,desired = self.depth_case()
        self.assertIsNotNone(result)
        self.assertTrue(result['depth'])
        # Coin camera projection stores float32 coordinates.
        self.assertLess((result['delta']-desired).Length,.1)
        self.assertEqual(result['key'][0],0)
        self.assertLess(source.translated(result['delta']).common(target).Volume,1e-7)

    def test_visible_top_face_resolves_perspective_depth(self):
        source,target,result,desired = self.depth_case(perspective=True)
        self.assertIsNotNone(result)
        self.assertTrue(result['depth'])
        self.assertAlmostEqual(result['delta'].z,44,places=5)
        self.assertGreater(source.translated(result['delta']).Faces[4].common(target.Faces[5]).Area,0)

    def test_depth_connection_checks_blocker_outside_initial_broadphase(self):
        source,target,result,desired = self.depth_case(blocker=True)
        self.assertTrue(result is None or not result.get('depth'))

    def test_depth_connection_cannot_break_axis_lock(self):
        source,target,result,desired = self.depth_case(axis='X')
        self.assertTrue(result is None or not result.get('depth'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
