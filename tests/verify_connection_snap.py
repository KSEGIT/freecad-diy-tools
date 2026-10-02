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


    def test_explicit_target_intent_prevents_nearby_part_stealing(self):
        side = Part.makeBox(1700,94,44,App.Vector(1800,105,10))
        result = connection_snap(self.source,[('NearSide',side),('EndBeam',self.target)],
            App.Vector(1702,10,10),lambda p:(p.x,p.y),
            intent={'target_index':1,'point':App.Vector(1700,47,22),'component':'Face2',
                    'source_pickup':App.Vector(0,47,22)})
        self.assertIsNotNone(result)
        self.assertEqual(result['label'],'EndBeam')
        self.vector(result['delta'],(1700,0,0))

    def test_release_radius_retains_joint_until_twenty_six_pixels(self):
        previous = self.snap((1710,0,0))
        retained = self.snap((1724,0,0),previous=previous)
        self.assertIsNotNone(retained)
        self.assertEqual(retained['key'],previous['key'])
        self.assertIsNone(self.snap((1728,0,0),previous=previous))

    def test_middle_grip_edge_intent_keeps_along_edge_position(self):
        source = Part.makeBox(800,44,44,App.Vector(300,50,44))
        target = Part.makeBox(1700,94,44)
        edge_index = next(i for i,e in enumerate(target.Edges)
                          if all(abs(v.Point.y-94)<1e-6 and abs(v.Point.z-44)<1e-6 for v in e.Vertexes))
        result = self.snap((0,2,0),source=source,targets=[('Rail',target)],
            intent={'target_index':0,'point':App.Vector(700,94,44),
                    'component':'Edge'+str(edge_index+1),'source_pickup':App.Vector(700,94,44)})
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['delta'].x,0,places=6)
        self.assertAlmostEqual(result['delta'].y,0,places=6)

    def adjacent_top(self, raw, axis=None, previous=None, blocker=None):
        source = Part.makeBox(44,94,900)
        target = Part.makeBox(1700,94,44)
        top = next(i for i,f in enumerate(target.Faces) if f.normalAt(0,0).z > .99)
        targets = [('Rail',target)]
        if blocker is not None:
            targets.append(('Blocker',blocker))
        result = self.snap(raw,source=source,targets=targets,axis=axis,previous=previous,
            intent={'target_index':0,'component':'Face'+str(top+1),
                    'point':App.Vector(1690,47,44),'source_pickup':App.Vector(22,47,0)})
        return source,target,result

    def test_near_end_face_contact_flushes_both_adjacent_planes(self):
        source,target,result = self.adjacent_top((1659,5,49))
        self.assertIsNotNone(result)
        self.vector(result['delta'],(1656,0,44))
        self.assertLess(source.translated(result['delta']).common(target).Volume,1e-7)
        self.assertAlmostEqual(source.translated(result['delta']).Faces[4].common(target.Faces[5]).Area,44*94)

    def test_adjacent_plane_capture_preserves_middle_rail_sliding(self):
        _,_,result = self.adjacent_top((800,5,49))
        self.assertIsNotNone(result)
        self.vector(result['delta'],(800,0,44))

    def test_adjacent_plane_capture_respects_axis_lock(self):
        _,_,result = self.adjacent_top((1659,5,49),axis='Z')
        self.assertIsNotNone(result)
        self.vector(result['delta'],(1659,5,44))

    def test_l_joint_flushes_top_and_side_with_middle_or_top_pickup(self):
        source = Part.makeBox(44,94,900)
        target = Part.makeBox(1700,94,44)
        end = next(i for i,f in enumerate(target.Faces) if f.normalAt(0,0).x > .99)
        for height in (450,890):
            result = self.snap((1704,5,-853),source=source,targets=[('Rail',target)],
                intent={'target_index':0,'component':'Face'+str(end+1),
                        'point':App.Vector(1700,47,40),
                        'source_pickup':App.Vector(0,47,height)})
            self.assertIsNotNone(result)
            self.vector(result['delta'],(1700,0,-856))
            moved = source.translated(result['delta'])
            self.assertAlmostEqual(moved.BoundBox.ZMax,target.BoundBox.ZMax)
            self.assertAlmostEqual(moved.BoundBox.YMin,target.BoundBox.YMin)
            self.assertAlmostEqual(moved.distToShape(target)[0],0)
            self.assertLess(moved.common(target).Volume,1e-7)

    def test_l_joint_zoom_capture_matches_normal_snap_radius(self):
        source = Part.makeBox(44,94,900)
        target = Part.makeBox(1700,94,44)
        end = next(i for i,f in enumerate(target.Faces) if f.normalAt(0,0).x > .99)
        intent = {'target_index':0,'component':'Face'+str(end+1),
                  'point':App.Vector(1700,47,40),'source_pickup':App.Vector(0,47,890)}
        # Physical screen pixels at a closer zoom: the complete correction is
        # inside normal 18px capture, but beyond the old extra 8px gate.
        project = lambda p:(p.y*2,p.z*2)
        result = connection_snap(source,[('Rail',target)],App.Vector(1704,5,-853),
                                 project,intent=intent)
        self.assertIsNotNone(result)
        self.vector(result['delta'],(1700,0,-856))
        outside = connection_snap(source,[('Rail',target)],App.Vector(1704,9,-853),
                                  project,intent=intent)
        self.assertIsNotNone(outside)
        self.assertEqual(outside.get('adjacent_planes',0),0)
        self.assertGreater((outside['delta']-App.Vector(1700,0,-856)).Length,1)

    def test_adjacent_complete_joint_retains_key_during_small_jitter(self):
        _,_,previous = self.adjacent_top((1659,5,49))
        for drift in (1,-1,2,-2):
            _,_,result = self.adjacent_top((1659+drift,5+drift,49),previous=previous)
            self.assertIsNotNone(result)
            self.assertEqual(result['key'],previous['key'])
            self.vector(result['delta'],(1656,0,44))

    def test_adjacent_complete_joint_does_not_pull_far_boundary(self):
        _,_,result = self.adjacent_top((1640,5,49))
        self.assertIsNotNone(result)
        self.vector(result['delta'],(1640,5,44))
        self.assertEqual(result.get('adjacent_planes',0),0)

    def test_adjacent_complete_joint_works_in_rotated_world_coordinates(self):
        source = Part.makeBox(44,94,900)
        target = Part.makeBox(1700,94,44)
        top = next(i for i,f in enumerate(target.Faces) if f.normalAt(0,0).z > .99)
        rotation = App.Rotation(App.Vector(1,2,3),37)
        placement = App.Placement(App.Vector(100,200,300),rotation)
        source.Placement = placement
        target.Placement = placement
        before_source,before_target = source.Placement,target.Placement
        def project(point):
            local = rotation.inverted().multVec(point-placement.Base)
            return local.x,local.y+local.z
        result = connection_snap(source,[('Rotated rail',target)],
            rotation.multVec(App.Vector(1659,5,49)),project,
            intent={'target_index':0,'component':'Face'+str(top+1),
                    'point':placement.multVec(App.Vector(1690,47,44)),
                    'source_pickup':placement.multVec(App.Vector(22,47,0))})
        self.assertIsNotNone(result)
        self.assertLess((result['delta']-rotation.multVec(App.Vector(1656,0,44))).Length,1e-6)
        self.assertEqual(source.Placement,before_source)
        self.assertEqual(target.Placement,before_target)

    def test_adjacent_complete_joint_obeys_collision_blockers(self):
        blocker = Part.makeBox(1,1,10,App.Vector(1699,0,44))
        source,target,result = self.adjacent_top((1659,5,49),blocker=blocker)
        self.assertIsNotNone(result)
        self.assertGreater((result['delta']-App.Vector(1656,0,44)).Length,1)
        self.assertLess(source.translated(result['delta']).common(blocker).Volume,1e-7)

    def test_explicit_intent_overrides_previous_other_target(self):
        first = self.snap((1710,0,0))
        second = Part.makeBox(1700,94,44,App.Vector(0,2,0))
        result = self.snap((1710,2,0),targets=[('Beam',self.target),('Chosen',second)],
            previous=first,intent={'target_index':1,'point':App.Vector(1700,49,22),
                'component':'Face2','source_pickup':App.Vector(0,47,22)})
        self.assertIsNotNone(result)
        self.assertEqual(result['label'],'Chosen')

    def test_intended_target_still_checks_other_collision_blockers(self):
        blocker = Part.makeBox(100,94,44,App.Vector(1750,0,0))
        result = self.snap((1710,0,0),targets=[('Beam',self.target),('Blocker',blocker)],
            intent={'target_index':0,'point':App.Vector(1700,47,22),'component':'Face2',
                    'source_pickup':App.Vector(0,47,22)})
        self.assertIsNone(result)

    def test_corner_pickup_matches_near_end_and_stays_stable_with_jitter(self):
        vertex_index = next(i for i,v in enumerate(self.target.Vertexes)
                            if (v.Point-App.Vector(1700,0,0)).Length < 1e-6)
        intent = {'target_index':0,'point':App.Vector(1700,0,0),
                  'component':'Vertex'+str(vertex_index+1),'source_pickup':App.Vector(0,0,0)}
        previous = self.snap((1705,2,1),intent=intent)
        self.assertIsNotNone(previous)
        self.vector(previous['delta'],(1700,0,0))
        for drift in (1,-1,2,-2):
            result = self.snap((1705,drift,1),intent=intent,previous=previous)
            self.assertIsNotNone(result)
            self.assertEqual(result['key'],previous['key'])
            self.vector(result['delta'],(1700,0,0))

    def test_retained_nearby_joint_survives_competing_small_jitter(self):
        source = Part.makeBox(100,10,10)
        first = Part.makeBox(100,10,10,App.Vector(0,20,0))
        second = Part.makeBox(100,10,10,App.Vector(0,21,0))
        previous = self.snap((0,10,0),source=source,targets=[('First',first)])
        result = self.snap((0,10.6,0),source=source,
                           targets=[('First',first),('Second',second)],previous=previous)
        self.assertIsNotNone(result)
        self.assertEqual(result['key'],previous['key'])

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

    def test_excluding_one_contact_keeps_other_face_contacts_and_blockers(self):
        raw = (1710,5,3)
        first = self.snap(raw)
        alternative = self.snap(raw, excluded_keys={first['key']})
        self.assertIsNotNone(alternative)
        self.assertNotEqual(alternative['key'],first['key'])
        self.assertEqual(alternative['key'][0],first['key'][0])
        blocker = Part.makeBox(20,20,20,App.Vector(1750,10,10))
        result = self.snap(raw, targets=[('Beam',self.target),('Blocker',blocker)],
                           excluded_keys={first['key']})
        if result is not None:
            self.assertLess(self.source.translated(result['delta']).common(blocker).Volume,1e-7)

    def test_visible_parallel_edge_flush_preserves_midrail_position(self):
        rail = Part.makeBox(1700,94,44)
        top = next(i for i, face in enumerate(rail.Faces) if face.normalAt(0,0).z > .99)
        for drift, expected in [(2,-2),(10,0)]:
            upright = Part.makeBox(44,94,900,App.Vector(300,drift,44))
            result = connection_snap(upright,[('Rail',rail)],App.Vector(),
                                     lambda p:(p.x,p.y+p.z),
                                     view_direction=App.Vector(1,1,1), depth_faces={0:{top}})
            self.assertIsNotNone(result)
            self.vector(result['delta'],(0,expected,0))
            self.assertEqual(result['kind'],'flush' if expected else 'face')
            self.assertLess(upright.translated(result['delta']).common(rail).Volume,1e-7)


if __name__ == '__main__':
    unittest.main(verbosity=2)
