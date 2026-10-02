"""Real FreeCAD geometry/Undo, Qt controls and Coin previews; view boundary simulated."""
from pathlib import Path
import sys, types, unittest
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'DIYWorkbenchTools'))
import FreeCAD as App, Part
from PySide import QtWidgets, QtCore, QtGui
from pivy import coin
application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
class View:
    def __init__(self):
        self.scene = coin.SoSeparator(); self.callbacks = []; self.pick = None
        self.visibility = {}
        self.camera = coin.SoOrthographicCamera(); self.camera.position.setValue(0, 0, 100); self.camera.height.setValue(200)
    def getSceneGraph(self): return self.scene
    def getCameraNode(self): return self.camera
    def getSize(self): return (200, 200)
    def getPointOnScreen(self, point): return (int(round(point.x+100)), int(round(point.y+100)))
    def getObjectInfo(self, position): return self.pick(position) if callable(self.pick) else self.pick
    def addEventCallbackPivy(self, kind, callback):
        self.callbacks.append((kind, callback)); return callback
    def removeEventCallbackPivy(self, kind, callback): self.callbacks.remove((kind, callback))
view = View()
gui = types.ModuleType('FreeCADGui')
gui.getMainWindow = lambda: None
gui.activeDocument = lambda: types.SimpleNamespace(activeView=lambda: view, getInEdit=lambda: None)
gui.activeWorkbench = lambda: types.SimpleNamespace(name=lambda: 'DIYWorkbench')
selection = []
gui.Selection = types.SimpleNamespace(clearSelection=selection.clear, getSelection=lambda: list(selection), getSelectionEx=lambda: [])
gui.addCommand = lambda *args: None
sys.modules['FreeCADGui'] = gui

class MagneticTests(unittest.TestCase):
    def setUp(self):
        global piece, view
        self.doc = App.newDocument('MagneticQtCheck'); self.doc.UndoMode = 1
        self.docname = self.doc.Name
        piece = self.doc.addObject('Part::Box', 'Source'); self.doc.recompute()
        view = View()
        selection[:] = [piece]
        module.set_snap_enabled(True)
        self.dialog = module.MagneticMoveDialog(piece, pickup_point=piece.Shape.CenterOfMass)
    def tearDown(self):
        if not self.dialog.closed:
            self.dialog.close()
        active = getattr(gui, '_workbench_magnetic_move_dialog', None)
        if active is not None:
            active.close()
        if self.docname in App.listDocuments():
            App.closeDocument(self.docname)
    def test_starts_with_centre_and_visible_ghost_without_source_click(self):
        self.assertEqual(tuple(self.dialog.source), (5., 5., 5.))
        self.assertEqual(self.dialog.ghost_switch.whichChild.getValue(), coin.SO_SWITCH_ALL)
        self.assertNotIn('corner', self.dialog.message.text().lower())
        self.assertLessEqual(self.dialog.maximumWidth(), 380)
    def test_first_motion_and_single_click_commit_then_undo(self):
        point = self.dialog.point_on_plane((125, 110))
        self.dialog.move((125, 110))
        self.assertLess((self.dialog.destination - point).Length, 1e-7)
        self.assertEqual(tuple(piece.Placement.Base), (0., 0., 0.))
        self.dialog.click((125, 110))
        self.assertLess((piece.Placement.Base - App.Vector(point.x-5, point.y-5, 0)).Length, 1e-7)
        self.assertTrue(self.dialog.closed)
        self.doc.undo(); self.assertLess(piece.Placement.Base.Length, 1e-7)
    def test_tree_selection_first_motion_does_not_jump(self):
        self.dialog.close()
        self.dialog = module.MagneticMoveDialog(piece)
        module.set_snap_enabled(False)
        self.dialog.move((160, 145))
        self.assertLess((self.dialog.destination - self.dialog.source).Length, 1e-7)
        self.dialog.move((170, 155))
        self.assertAlmostEqual(self.dialog.destination.x - self.dialog.source.x, 10, places=5)
        self.assertAlmostEqual(self.dialog.destination.y - self.dialog.source.y, 10, places=4)
        self.dialog.click((170, 155))
        self.assertAlmostEqual(piece.Placement.Base.x, 10, places=5)
        self.doc.undo(); self.assertLess(piece.Placement.Base.Length, 1e-7)

    def test_native_picked_point_is_preserved_before_selection_clear(self):
        self.dialog.close()
        selected = types.SimpleNamespace(Object=piece, PickedPoints=[App.Vector(10, 3, 7)])
        original = gui.Selection.getSelectionEx
        try:
            gui.Selection.getSelectionEx = lambda: [selected] if selection else []
            selection[:] = [piece]
            self.dialog = module.MagneticMoveDialog(piece)
            self.assertEqual(tuple(self.dialog.source + self.dialog.pickup_offset), (10., 3., 7.))
            self.assertTrue(self.dialog.has_pickup)
            self.assertEqual(selection, [])
            self.dialog.move((110, 103))
            self.assertLess((self.dialog.destination - self.dialog.source).Length, 1e-5)
        finally:
            gui.Selection.getSelectionEx = original

    def test_native_long_beam_grip_near_edge_keeps_pickup_without_jump(self):
        self.dialog.close(); piece.Length = 1000; piece.Width = 94; piece.Height = 44
        self.doc.recompute(); point = App.Vector(500, 2, 44)
        old = gui.Selection.getSelectionEx
        try:
            gui.Selection.getSelectionEx = lambda: [types.SimpleNamespace(Object=piece, PickedPoints=[point])]
            self.dialog = module.MagneticMoveDialog(piece)
            self.assertAlmostEqual(self.dialog.source.y, 0)
            self.assertAlmostEqual(self.dialog.source.x, 500)
            module.set_snap_enabled(False); self.dialog.move((600, 102))
            self.assertLess((self.dialog.destination-self.dialog.source).Length, 1e-5)
            self.dialog.set_axis('Y'); self.dialog.move((600, 102))
            self.assertLess((self.dialog.destination-self.dialog.source).Length, 1e-5)
        finally:
            gui.Selection.getSelectionEx = old

    def test_direct_edge_intent_has_adjacent_faces_and_keeps_collision_targets(self):
        target = self.target(); other = self.target('Other', App.Vector(80, 0, 0))
        edge = target.Shape.Edges[0]
        point = edge.CenterOfMass
        view.pick = {'Document': self.docname, 'Object': target.Name, 'Component': 'Edge1',
                     'x': point.x, 'y': point.y, 'z': point.z}
        old = module.connection_snap; calls = []
        try:
            def inspect(*args, **kwargs):
                calls.append((args[1], kwargs)); return None
            module.connection_snap = inspect
            self.dialog.find_connection(App.Vector(40, 0, 0), (150, 105))
            targets, options = calls[0]
            self.assertEqual(len(targets), 2)
            self.assertEqual(options['intent']['target_index'], 0)
            self.assertEqual(options['intent']['component'], 'Edge1')
            self.assertEqual(len(options['depth_faces'][0]), 2)
        finally:
            module.connection_snap = old

    def test_acquired_target_survives_boundary_jitter_then_releases(self):
        target = self.target(); other = self.target('Other', App.Vector(60, 0, 0))
        self.dialog.targets()
        self.dialog.connection = {'key': (0, target.Label, 0), 'target': App.Vector(50, 5, 5),
                                  '_target_name': target.Name, '_cursor': (150, 105), 'target_face_index': 0}
        view.pick = {'Document': self.docname, 'Object': other.Name, 'Component': 'Face1',
                     'x': 60., 'y': 5., 'z': 5.}
        old = module.connection_snap; intentions = []
        try:
            module.connection_snap = lambda *args, **kwargs: intentions.append(kwargs['intent']) or None
            self.dialog.find_connection(App.Vector(40, 0, 0), (160, 105))
            self.assertEqual(intentions[-1]['target_index'], 0)
            self.dialog.find_connection(App.Vector(40, 0, 0), (180, 105))
            self.assertEqual(intentions[-1]['target_index'], 1)
        finally:
            module.connection_snap = old

    def test_remote_beam_end_cannot_probe_distant_object(self):
        self.dialog.close(); piece.Length = 1700; self.doc.recompute()
        self.dialog = module.MagneticMoveDialog(piece, pickup_point=piece.Shape.CenterOfMass)
        target = self.target(base=App.Vector(1700, 0, 100))
        pixels = []
        def pick(position):
            pixels.append(position)
            if position[0] > 1500:
                return {'Document': self.docname, 'Object': target.Name, 'Component': 'Face6'}
            return None
        view.pick = pick
        self.assertEqual(self.dialog.depth_faces(self.dialog.targets(), App.Vector(), (950, 105)), {})
        self.assertTrue(all(abs(p[0]-950) <= 40 and abs(p[1]-105) <= 40 for p in pixels))

    def test_snap_setting_and_s_key_toggle_active_session(self):
        module.set_snap_enabled(True)
        event = coin.SoKeyboardEvent(); event.setKey(coin.SoKeyboardEvent.S)
        event.setState(coin.SoButtonEvent.DOWN)
        callback = types.SimpleNamespace(getEvent=lambda: event, setHandled=lambda: None)
        self.dialog.handle_event(callback)
        self.assertFalse(module.snap_enabled())
        self.assertFalse(self.dialog.snap_button.isChecked())
        module.MagneticMove().Activated()
        self.assertTrue(module.snap_enabled()); self.assertTrue(self.dialog.snap_button.isChecked())
    def test_checkbox_and_command_keep_native_action_in_sync_without_restarting(self):
        action = QtGui.QAction('Auto snap', self.dialog)
        gui.Command = types.SimpleNamespace(get=lambda name: types.SimpleNamespace(getAction=lambda: [action]))
        try:
            module.set_snap_enabled(True)
            self.assertTrue(action.isCheckable()); self.assertTrue(action.isChecked())
            self.dialog.snap_button.setChecked(False)
            self.assertFalse(action.isChecked())
            module.MagneticMove().Activated(1)
            self.assertTrue(action.isChecked()); self.assertTrue(self.dialog.snap_button.isChecked())
            self.assertFalse(self.dialog.closed)
            self.assertEqual(len(view.callbacks), 1)
            self.assertEqual(tuple(piece.Placement.Base), (0., 0., 0.))
        finally:
            del gui.Command
            gui._workbench_snap_actions = []
    def test_reentry_reuses_source_and_removes_old_session(self):
        gui._workbench_magnetic_move_dialog = self.dialog
        module.start_move()
        replacement = gui._workbench_magnetic_move_dialog
        self.assertTrue(self.dialog.closed); self.assertIs(replacement.part, piece)
        self.assertEqual(len(view.callbacks), 1)
        replacement.close()
    def test_invalid_reentry_closes_old_session_before_selection_notice(self):
        self.doc.removeObject(piece.Name)
        original = QtWidgets.QMessageBox.information; notices = []
        try:
            def notice(*args):
                self.assertTrue(self.dialog.closed)
                self.assertEqual(view.callbacks, []); self.assertEqual(view.scene.getNumChildren(), 0)
                notices.append(args[-1])
            QtWidgets.QMessageBox.information = notice
            module.start_move()
            self.assertEqual(len(notices), 1)
            self.assertIsNone(gui._workbench_magnetic_move_dialog)
        finally:
            QtWidgets.QMessageBox.information = original
    def test_compact_controls_are_placed_at_main_window_edge(self):
        self.dialog.close()
        window = QtWidgets.QMainWindow(); window.setGeometry(100, 100, 1000, 700)
        original = gui.getMainWindow
        try:
            gui.getMainWindow = lambda: window
            self.dialog = module.MagneticMoveDialog(piece, pickup_point=piece.Shape.CenterOfMass)
            edge = window.mapToGlobal(window.rect().topRight())
            self.assertEqual(self.dialog.x(), edge.x()-390)
            self.assertEqual(self.dialog.y(), edge.y()+70)
            self.assertLessEqual(self.dialog.maximumWidth(), 380)
        finally:
            self.dialog.close(); gui.getMainWindow = original; window.close()
    def test_preview_cancel_never_changes_placement_and_removes_callbacks(self):
        original = piece.Placement
        self.dialog.preview(App.Vector(12, 7, 4), 'Cursor')
        self.assertEqual(piece.Placement, original)
        self.assertEqual(view.scene.getNumChildren(), 1)
        self.assertEqual(self.dialog.preview_root.getChild(0).style.getValue(), coin.SoPickStyle.UNPICKABLE)
        self.assertIn('7.00', self.dialog.message.text())
        self.dialog.close()
        self.assertEqual(view.scene.getNumChildren(), 0)
        self.assertEqual(view.callbacks, [])
        self.assertEqual(piece.Placement, original)
    def test_axis_distance_commit_is_one_undo_and_keeps_rotation(self):
        self.dialog.close()
        piece.Placement = App.Placement(App.Vector(), App.Rotation(App.Vector(0, 0, 1), 30))
        self.doc.recompute(); self.dialog = module.MagneticMoveDialog(piece, pickup_point=piece.Shape.CenterOfMass); rotation = piece.Placement.Rotation
        self.dialog.set_axis('X'); self.dialog.distance.setValue(-25)
        self.dialog.apply_distance()
        self.assertAlmostEqual(piece.Placement.Base.x, -25)
        self.assertAlmostEqual(piece.Placement.Base.y, 0)
        self.assertEqual(piece.Placement.Rotation, rotation)
        self.assertTrue(self.dialog.closed); self.doc.undo()
        self.assertLess(piece.Placement.Base.Length, 1e-7)
    def test_navigation_mouse_buttons_are_not_consumed(self):
        for button in (coin.SoMouseButtonEvent.BUTTON2, coin.SoMouseButtonEvent.BUTTON3):
            event = coin.SoMouseButtonEvent(); event.setButton(button); event.setState(coin.SoButtonEvent.DOWN)
            callback = types.SimpleNamespace(getEvent=lambda: event, handled=False)
            callback.setHandled = lambda: setattr(callback, 'handled', True)
            callback.isHandled = lambda: callback.handled
            self.dialog.handle_event(callback); self.assertFalse(callback.isHandled())
    def test_deleted_source_and_switched_view_cancel(self):
        self.doc.removeObject(piece.Name); self.dialog.check_context()
        self.assertTrue(self.dialog.closed); self.assertEqual(view.callbacks, [])
    def test_view_switch_cancels_without_changes(self):
        global view
        old = view; view = View(); self.dialog.check_context()
        self.assertTrue(self.dialog.closed); self.assertEqual(old.callbacks, [])
        self.assertEqual(old.scene.getNumChildren(), 0)
    def test_perspective_cursor_uses_plane_through_anchor(self):
        self.dialog.source = App.Vector(3, 4, 20)
        view.camera = coin.SoPerspectiveCamera(); view.camera.position.setValue(0, 0, 100)
        point = self.dialog.point_on_plane((100, 100))
        self.assertAlmostEqual(point.z, 20, places=5)
        self.assertAlmostEqual(point.x, 0, places=5)
        self.assertAlmostEqual(point.y, 0, places=5)
        self.dialog.set_axis('Z'); self.dialog.move((110, 100))
        self.assertTrue(all(abs(v) < 1e8 for v in (self.dialog.destination.x, self.dialog.destination.y, self.dialog.destination.z)))
    def target(self, name='Target', base=App.Vector(50, 0, 0)):
        target = self.doc.addObject('Part::Box', name); target.Placement.Base = base
        self.doc.recompute(); return target
    def pick_target(self, target):
        # These fixtures isolate the existing short-distance path. Actual
        # bounded FaceN cursor probes are covered by the depth contact test.
        self.dialog.depth_faces = lambda targets, raw_delta, position: {}
        def pick(position):
            x, y = position[0]-100, position[1]-100
            if abs(x-target.Placement.Base.x) > .001 or not target.Placement.Base.y <= y <= target.Placement.Base.y+target.Width.Value:
                return None
            face = next(i+1 for i, f in enumerate(target.Shape.Faces)
                        if abs(f.CenterOfMass.x-target.Placement.Base.x) < 1e-7)
            return {'Document': self.doc.Name, 'Object': target.Name, 'Component': 'Face' + str(face),
                    'x': x, 'y': y, 'z': target.Placement.Base.z+5.}
        view.pick = pick
    def test_inferred_end_connection_refreshes_target_and_commits_once(self):
        target = self.target(); self.pick_target(target)
        self.dialog.move((148, 105))
        self.assertIsNotNone(self.dialog.connection)
        self.assertAlmostEqual(self.dialog.destination.x - self.dialog.source.x, 40)
        self.assertEqual(self.dialog.lines.numVertices.getNum(), 3)
        self.assertIn(target.Label, self.dialog.message.text())
        self.assertEqual(tuple(piece.Placement.Base), (0., 0., 0.))
        target.Placement.Base.x = 75; self.doc.recompute()
        self.dialog.click((173, 105))
        self.assertAlmostEqual(piece.Placement.Base.x, 65)
        self.assertTrue(self.dialog.closed)
        self.doc.undo(); self.assertLess(piece.Placement.Base.Length, 1e-7)
    def test_visible_face_probe_allows_real_camera_depth_contact_beyond_50_mm(self):
        target = self.target(base=App.Vector(50, 0, 100))
        view.camera.position.setValue(0, 0, 1000)
        top = next(i for i, f in enumerate(target.Shape.Faces)
                   if abs(f.CenterOfMass.z - 110) < 1e-7)
        def pick(position):
            x, y = position[0] - 100, position[1] - 100
            if 50 <= x <= 60 and 0 <= y <= 10:
                return {'Document': self.docname, 'Object': target.Name,
                        'Component': 'Face' + str(top + 1), 'x': x, 'y': y, 'z': 110.}
            return None
        view.pick = pick
        self.dialog.move((155, 105))
        self.assertIsNotNone(self.dialog.connection)
        self.assertTrue(self.dialog.connection['depth'])
        self.assertGreater(abs(self.dialog.connection['delta'].z), 50)
        moved = piece.Shape.copy(); moved.translate(self.dialog.connection['delta'])
        self.assertLess(moved.common(target.Shape).Volume, 1e-7)
        self.assertLess(moved.distToShape(target.Shape)[0], 1e-7)
        self.dialog.click((155, 105))
        self.assertTrue(self.dialog.closed)
        self.doc.undo(); self.assertLess(piece.Placement.Base.Length, 1e-7)

    def test_depth_contact_cannot_use_a_hidden_rear_face(self):
        target = self.target()
        top = next(i for i, f in enumerate(target.Shape.Faces)
                   if abs(f.CenterOfMass.z - 10) < 1e-7)
        view.pick = {'Document': self.docname, 'Object': target.Name,
                     'Component': 'Face' + str(top + 1)}
        old = module.connection_snap
        try:
            module.connection_snap = lambda *args, **kwargs: {
                'delta': App.Vector(50, 0, 100), 'source': App.Vector(),
                'target': App.Vector(50, 0, 100), 'label': target.Label,
                'kind': 'face', 'key': (0, target.Label, 1, 0),
                'depth': True, 'target_face_index': (top + 1) % 6}
            self.assertIsNone(self.dialog.find_connection(App.Vector(50, 0, 0), (150, 100)))
        finally:
            module.connection_snap = old

    def test_occlusion_retry_keeps_all_solids_as_collision_obstacles(self):
        target = self.target()
        blocker = self.target('Blocker', App.Vector(50, 0, 300))
        view.pick = {'Document': self.docname, 'Object': blocker.Name, 'Component': 'Face1'}
        old = module.connection_snap; calls = []
        try:
            def candidate(source, targets, delta, project, **kwargs):
                calls.append((len(targets), set(kwargs['excluded_keys'])))
                if len(calls) > 1:
                    return None
                return {'delta': App.Vector(40, 0, 0), 'source': App.Vector(),
                        'target': App.Vector(50, 0, 0), 'label': target.Label,
                        'kind': 'face', 'key': (0, target.Label, 1, 0), 'depth': False}
            module.connection_snap = candidate
            self.assertIsNone(self.dialog.find_connection(App.Vector(43, 0, 0), (148, 105)))
            self.assertEqual(calls, [(2, set()), (2, {(0, target.Label, 1, 0)})])
        finally:
            module.connection_snap = old

    def test_all_box_face_centres_are_probed_with_bounded_budget(self):
        target = self.target()
        wanted = tuple(int(round(v)) for v in view.getPointOnScreen(self.dialog.source_shape.Faces[-1].CenterOfMass))
        pixels = []
        def pick(position):
            pixels.append(position)
            if position == wanted:
                return {'Document': self.docname, 'Object': target.Name, 'Component': 'Face6'}
            return None
        view.pick = pick
        self.assertEqual(self.dialog.depth_faces(self.dialog.targets(), App.Vector(), (125, 125)), {0: {5}})
        self.assertIn(wanted, pixels)
        self.assertLessEqual(len(pixels), 33)

    def test_depth_probe_ignores_source_and_nested_hits(self):
        target = self.target()
        targets = self.dialog.targets()
        for info in ({'Document': self.docname, 'Object': piece.Name, 'Component': 'Face1'},
                     {'Document': self.docname, 'Object': target.Name, 'Component': 'Face1', 'ParentObject': 'Container'}):
            view.pick = info
            self.assertEqual(self.dialog.depth_faces(targets, App.Vector(), (105, 105)), {})

    def test_toggle_off_releases_current_snap_and_moving_away_stays_free(self):
        target = self.target(); self.pick_target(target)
        self.dialog.move((148, 105))
        self.assertAlmostEqual(self.dialog.destination.x, 45)
        self.dialog.snap_button.setChecked(False)
        self.assertIsNone(self.dialog.connection)
        self.assertEqual(self.dialog.lines.numVertices.getNum(), 2)
        self.assertAlmostEqual(self.dialog.destination.x, 48)
        self.dialog.snap_button.setChecked(True)
        self.assertAlmostEqual(self.dialog.destination.x, 45)
        self.dialog.move((10, 150))
        self.assertIsNone(self.dialog.connection)
    def test_connection_is_retained_just_outside_pixel_capture_then_releases(self):
        self.dialog.close(); piece.Length = 100; self.doc.recompute()
        self.dialog = module.MagneticMoveDialog(piece, pickup_point=App.Vector(100, 5, 5))
        target = self.target(base=App.Vector(200, 0, 0)); target.Length = 100; self.doc.recompute()
        self.pick_target(target); self.dialog.set_axis('X')
        self.dialog.move((293, 105))
        self.assertAlmostEqual(self.dialog.destination.x - self.dialog.source.x, 100)
        self.dialog.move((319, 105))
        self.assertIsNotNone(self.dialog.connection)
        self.assertAlmostEqual(self.dialog.destination.x - self.dialog.source.x, 100)
        self.dialog.move((335, 105)); self.assertIsNone(self.dialog.connection)
    def test_explicit_foreground_target_cannot_snap_to_rear_object(self):
        target = self.target(); blocker = self.target('Blocker', App.Vector(50, 0, 300))
        self.pick_target(blocker)
        view.pick = {'Document': self.docname, 'Object': blocker.Name, 'Component': 'Face1'}
        self.dialog.move((148, 105))
        self.assertIsNotNone(self.dialog.connection)
        self.assertEqual(self.dialog.connection['_target_name'], blocker.Name)
        self.assertLessEqual(self.dialog.capture_distance((148, 105)), 50)
    def test_duplicate_label_does_not_make_occluded_joint_visible(self):
        target = self.target(); blocker = self.target('Blocker', App.Vector(50, 0, 300))
        blocker.Label = target.Label
        self.pick_target(blocker)
        view.pick = {'Document': self.docname, 'Object': blocker.Name, 'Component': 'Face1'}
        self.dialog.move((148, 105))
        self.assertIsNotNone(self.dialog.connection)
        self.assertEqual(self.dialog.connection['_target_name'], blocker.Name)
    def test_nested_object_occluding_target_cannot_be_treated_as_empty_pixel(self):
        self.target(); blocker = self.target('Blocker', App.Vector(50, 0, 300))
        container = self.doc.addObject('App::Part', 'Container'); container.addObject(blocker)
        self.pick_target(blocker)
        view.pick = {'Document': self.docname, 'Object': blocker.Name, 'Component': 'Face1'}
        self.dialog.move((148, 105))
        self.assertIsNone(self.dialog.connection)
    def test_coin_first_motion_and_click_use_event_position_without_pickup(self):
        event = coin.SoLocation2Event(); event.setPosition(coin.SbVec2s(125, 110))
        callback = types.SimpleNamespace(getEvent=lambda: event, setHandled=lambda: None)
        self.dialog.handle_event(callback)
        self.assertAlmostEqual(self.dialog.destination.x, 25)
        event = coin.SoMouseButtonEvent(); event.setPosition(coin.SbVec2s(125, 110))
        event.setButton(coin.SoMouseButtonEvent.BUTTON1); event.setState(coin.SoButtonEvent.DOWN)
        self.dialog.handle_event(callback)
        self.assertAlmostEqual(piece.Placement.Base.x, 20)
        self.assertTrue(self.dialog.closed)
    def test_hidden_source_and_nested_objects_are_excluded(self):
        visible = self.target(); hidden = self.target('Hidden', App.Vector(80, 0, 0))
        view.visibility[hidden.Name] = False
        container = self.doc.addObject('App::Part', 'Container')
        nested = self.target('Nested', App.Vector(100, 0, 0)); container.addObject(nested)
        labels = [c[0] for c in self.dialog.targets()]
        self.assertTrue(labels); self.assertTrue(all(c.startswith(visible.Label) for c in labels))
        view.visibility[visible.Name] = False
        self.assertEqual(self.dialog.targets(), [])
    def test_source_geometry_change_cancels_stale_anchor(self):
        piece.Length = 30; self.doc.recompute(); self.dialog.check_context()
        self.assertTrue(self.dialog.closed); self.assertEqual(view.scene.getNumChildren(), 0)
    def test_escape_coin_event_cancels(self):
        event = coin.SoKeyboardEvent(); event.setKey(coin.SoKeyboardEvent.ESCAPE)
        event.setState(coin.SoButtonEvent.DOWN)
        callback = types.SimpleNamespace(getEvent=lambda: event, setHandled=lambda: None)
        self.dialog.handle_event(callback)
        self.assertTrue(self.dialog.closed); self.assertEqual(view.callbacks, [])
    def test_workbench_switch_cancels(self):
        prior = gui.activeWorkbench
        try:
            gui.activeWorkbench = lambda: types.SimpleNamespace(name=lambda: 'PartWorkbench')
            self.dialog.check_context(); self.assertTrue(self.dialog.closed)
        finally:
            gui.activeWorkbench = prior
    def test_closed_document_cancels_without_leaking_nodes(self):
        name = self.doc.Name
        App.closeDocument(name); self.dialog.check_context()
        self.assertTrue(self.dialog.closed); self.assertEqual(view.callbacks, [])
        self.assertEqual(view.scene.getNumChildren(), 0)
    def test_modified_left_mouse_navigation_preserves_placement(self):
        event = coin.SoMouseButtonEvent(); event.setButton(coin.SoMouseButtonEvent.BUTTON1)
        event.setState(coin.SoButtonEvent.DOWN); event.setCtrlDown(True)
        callback = types.SimpleNamespace(getEvent=lambda: event, handled=False)
        callback.setHandled = lambda: setattr(callback, 'handled', True)
        self.dialog.handle_event(callback)
        self.assertFalse(callback.handled); self.assertFalse(self.dialog.closed)
        self.assertEqual(tuple(piece.Placement.Base), (0., 0., 0.))
    def test_coin_axis_keyboard_and_typed_distance_survive_hover(self):
        event = coin.SoKeyboardEvent(); event.setKey(coin.SoKeyboardEvent.X)
        event.setState(coin.SoButtonEvent.DOWN)
        callback = types.SimpleNamespace(getEvent=lambda: event, setHandled=lambda: None)
        self.dialog.handle_event(callback); self.assertEqual(self.dialog.axis, 'X')
        self.dialog.distance.setValue(-37.25); self.dialog.move((110, 100))
        self.assertEqual(self.dialog.distance.value(), -37.25)
        self.assertFalse(self.dialog.closed)
    def test_error_during_hover_removes_preview_without_model_change(self):
        def broken_camera_size():
            raise RuntimeError('Expected view failure fixture')
        view.getSize = broken_camera_size
        event = coin.SoLocation2Event(); event.setPosition(coin.SbVec2s(50, 0))
        callback = types.SimpleNamespace(getEvent=lambda: event, setHandled=lambda: None)
        self.dialog.handle_event(callback)
        self.assertTrue(self.dialog.closed); self.assertEqual(view.callbacks, [])
        self.assertEqual(view.scene.getNumChildren(), 0)
        self.assertEqual(tuple(piece.Placement.Base), (0., 0., 0.))
    def test_document_switch_cancels(self):
        other = App.newDocument('OtherMagneticCheck')
        self.dialog.check_context(); self.assertTrue(self.dialog.closed)
        App.closeDocument(other.Name)
if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1] / 'DIYWorkbenchTools' / 'WorkbenchMagneticMove.py'
    assert path.exists(), 'Magnetic Move session is not implemented'
    # FreeCAD adds installed Mod folders to sys.path while importing App.
    # Restore this checkout first so helpers are tested from this branch.
    sys.path.insert(0, str(path.parent))
    for name in ('WorkbenchPlacement', 'WorkbenchMagneticGeometry', 'WorkbenchMagneticMove'):
        sys.modules.pop(name, None)
    import WorkbenchMagneticMove as module
    import inspect
    assert Path(inspect.getsourcefile(module.connection_snap)).parent == path.parent
    # Visibility is view-provider state; headless FreeCAD has no ViewObjects.
    module._visible = lambda obj: view.visibility.get(obj.Name, True)
    unittest.main()
