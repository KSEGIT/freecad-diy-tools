"""Real FreeCAD geometry/Undo, Qt controls and Coin previews; view boundary simulated."""
from pathlib import Path
import sys, types, unittest
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'DIYWorkbenchTools'))
import FreeCAD as App, Part
from PySide import QtWidgets, QtCore
from pivy import coin
application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
class View:
    def __init__(self):
        self.scene = coin.SoSeparator(); self.callbacks = []; self.pick = None
        self.visibility = {}
        self.camera = coin.SoOrthographicCamera(); self.camera.position.setValue(0, 0, 100)
    def getSceneGraph(self): return self.scene
    def getCameraNode(self): return self.camera
    def getSize(self): return (200, 200)
    def getPointOnScreen(self, point): return (int(round(point.x)), int(round(point.y)))
    def getObjectInfo(self, position): return self.pick(position) if callable(self.pick) else self.pick
    def addEventCallbackPivy(self, kind, callback):
        self.callbacks.append((kind, callback)); return callback
    def removeEventCallbackPivy(self, kind, callback): self.callbacks.remove((kind, callback))
view = View()
gui = types.ModuleType('FreeCADGui')
gui.getMainWindow = lambda: None
gui.activeDocument = lambda: types.SimpleNamespace(activeView=lambda: view, getInEdit=lambda: None)
gui.activeWorkbench = lambda: types.SimpleNamespace(name=lambda: 'DIYWorkbench')
gui.Selection = types.SimpleNamespace(clearSelection=lambda: None, getSelection=lambda: [piece])
gui.addCommand = lambda *args: None
sys.modules['FreeCADGui'] = gui

class MagneticTests(unittest.TestCase):
    def setUp(self):
        global piece, view
        self.doc = App.newDocument('MagneticQtCheck'); self.doc.UndoMode = 1
        self.docname = self.doc.Name
        piece = self.doc.addObject('Part::Box', 'Source'); self.doc.recompute()
        view = View()
        self.dialog = module.MagneticMoveDialog(piece)
    def tearDown(self):
        self.dialog.close()
        if self.docname in App.listDocuments():
            App.closeDocument(self.docname)
    def anchor(self):
        view.pick = {'Document': self.doc.Name, 'Object': piece.Name, 'Component': 'Vertex1', 'x': 0., 'y': 0., 'z': 0.}
        self.dialog.click((0, 0))
        self.assertIsNotNone(self.dialog.source)
    def test_preview_cancel_never_changes_placement_and_removes_callbacks(self):
        original = piece.Placement
        self.anchor(); self.dialog.preview(App.Vector(12, 7, 4), 'Cursor')
        self.assertEqual(piece.Placement, original)
        self.assertEqual(view.scene.getNumChildren(), 1)
        self.assertEqual(self.dialog.preview_root.getChild(0).style.getValue(), coin.SoPickStyle.UNPICKABLE)
        self.assertIn('12.00', self.dialog.message.text())
        self.dialog.close()
        self.assertEqual(view.scene.getNumChildren(), 0)
        self.assertEqual(view.callbacks, [])
        self.assertEqual(piece.Placement, original)
    def test_axis_distance_commit_is_one_undo_and_keeps_rotation(self):
        self.dialog.close()
        piece.Placement = App.Placement(App.Vector(), App.Rotation(App.Vector(0, 0, 1), 30))
        self.doc.recompute(); self.dialog = module.MagneticMoveDialog(piece); rotation = piece.Placement.Rotation
        self.anchor(); self.dialog.set_axis('X'); self.dialog.distance.setValue(-25)
        self.dialog.apply_distance()
        self.assertAlmostEqual(piece.Placement.Base.x, -25)
        self.assertAlmostEqual(piece.Placement.Base.y, 0)
        self.assertEqual(piece.Placement.Rotation, rotation)
        self.assertTrue(self.dialog.closed); self.doc.undo()
        self.assertLess(piece.Placement.Base.Length, 1e-7)
    def test_wrong_source_click_cannot_choose_anchor(self):
        other = self.doc.addObject('Part::Box', 'Other'); self.doc.recompute()
        view.pick = {'Document': self.doc.Name, 'Object': other.Name, 'Component': 'Vertex1', 'x': 0., 'y': 0., 'z': 0.}
        self.dialog.click((0, 0)); self.assertIsNone(self.dialog.source)
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
        self.anchor(); self.dialog.source = App.Vector(3, 4, 20)
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
        def pick(position):
            face = next((i+1 for i, f in enumerate(target.Shape.Faces) if abs(f.CenterOfMass.z-10) < 1e-7), 1)
            return {'Document': self.doc.Name, 'Object': target.Name, 'Component': 'Face' + str(face), 'x': float(position[0]), 'y': float(position[1]), 'z': 10.}
        view.pick = pick
    def test_source_uses_clicked_vertex_when_back_corner_projects_same_pixel(self):
        vertex_index = next(i+1 for i, v in enumerate(piece.Shape.Vertexes) if tuple(v.Point) == (0., 0., 0.))
        view.pick = {'Document': self.doc.Name, 'Object': piece.Name, 'Component': 'Vertex' + str(vertex_index), 'x': 0., 'y': 0., 'z': 0.}
        self.dialog.click((0, 0))
        self.assertEqual(tuple(self.dialog.source), (0., 0., 0.))
    def test_target_rear_vertices_cannot_override_front_surface(self):
        self.anchor(); target = self.target()
        target.Placement = App.Placement(App.Vector(50, 0, 10), App.Rotation(App.Vector(1, 0, 0), 180))
        self.doc.recompute(); self.pick_target(target)
        self.dialog.move((50, 0))
        self.assertEqual(self.dialog.destination.z, 10.)
    def test_hover_snap_click_commits_exact_target_and_refreshes_moved_target(self):
        self.anchor(); target = self.target()
        self.pick_target(target)
        self.dialog.move((50, 0))
        self.assertAlmostEqual(self.dialog.destination.x, 50)
        self.assertIn('vertex', self.dialog.message.text())
        self.assertEqual(piece.Placement.Base.x, 0)
        target.Placement.Base = App.Vector(75, 0, 0); self.doc.recompute()
        self.dialog.click((75, 0))
        self.assertAlmostEqual(piece.Placement.Base.x, 75)
        self.assertTrue(self.dialog.closed)
    def test_hidden_source_and_nested_objects_are_excluded(self):
        self.anchor(); visible = self.target(); hidden = self.target('Hidden', App.Vector(80, 0, 0))
        view.visibility[hidden.Name] = False
        container = self.doc.addObject('App::Part', 'Container')
        nested = self.target('Nested', App.Vector(100, 0, 0)); container.addObject(nested)
        labels = [c[2] for c in self.dialog.targets()]
        self.assertTrue(labels); self.assertTrue(all(c.startswith(visible.Label) for c in labels))
        view.visibility[visible.Name] = False
        self.assertEqual(self.dialog.targets(), [])
    def test_planar_face_uses_surface_pick_not_centre(self):
        self.anchor(); target = self.target(); target.Length = 100; target.Width = 100; self.doc.recompute()
        face_name = next('Face' + str(i+1) for i, f in enumerate(target.Shape.Faces) if abs(f.CenterOfMass.z) < 1e-7)
        view.pick = {'Document': self.doc.Name, 'Object': target.Name, 'Component': face_name, 'x': 82., 'y': 37., 'z': 0.}
        self.dialog.move((82, 37))
        self.assertEqual(tuple(self.dialog.destination), (82., 37., 0.))
        self.assertIn('face', self.dialog.message.text())
    def test_source_geometry_change_cancels_stale_anchor(self):
        self.anchor(); piece.Length = 30; self.doc.recompute(); self.dialog.check_context()
        self.assertTrue(self.dialog.closed); self.assertEqual(view.scene.getNumChildren(), 0)
    def test_escape_coin_event_cancels(self):
        self.anchor(); event = coin.SoKeyboardEvent(); event.setKey(coin.SoKeyboardEvent.ESCAPE)
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
        self.anchor(); name = self.doc.Name
        App.closeDocument(name); self.dialog.check_context()
        self.assertTrue(self.dialog.closed); self.assertEqual(view.callbacks, [])
        self.assertEqual(view.scene.getNumChildren(), 0)
    def test_coin_motion_and_left_click_use_actual_event_pixel_position(self):
        self.anchor(); target = self.target(); self.pick_target(target)
        event = coin.SoLocation2Event(); event.setPosition(coin.SbVec2s(50, 0))
        callback = types.SimpleNamespace(getEvent=lambda: event, setHandled=lambda: None)
        self.dialog.handle_event(callback)
        self.assertEqual(tuple(self.dialog.destination), (50., 0., 10.))
        event = coin.SoMouseButtonEvent(); event.setPosition(coin.SbVec2s(50, 0))
        event.setButton(coin.SoMouseButtonEvent.BUTTON1); event.setState(coin.SoButtonEvent.DOWN)
        self.dialog.handle_event(callback)
        self.assertEqual(tuple(piece.Placement.Base), (50., 0., 0.)); self.assertTrue(self.dialog.closed)
    def test_modified_left_mouse_navigation_preserves_placement(self):
        self.anchor()
        event = coin.SoMouseButtonEvent(); event.setButton(coin.SoMouseButtonEvent.BUTTON1)
        event.setState(coin.SoButtonEvent.DOWN); event.setCtrlDown(True)
        callback = types.SimpleNamespace(getEvent=lambda: event, handled=False)
        callback.setHandled = lambda: setattr(callback, 'handled', True)
        self.dialog.handle_event(callback)
        self.assertFalse(callback.handled); self.assertFalse(self.dialog.closed)
        self.assertEqual(tuple(piece.Placement.Base), (0., 0., 0.))
    def test_coin_axis_keyboard_and_typed_distance_survive_hover(self):
        self.anchor(); event = coin.SoKeyboardEvent(); event.setKey(coin.SoKeyboardEvent.X)
        event.setState(coin.SoButtonEvent.DOWN)
        callback = types.SimpleNamespace(getEvent=lambda: event, setHandled=lambda: None)
        self.dialog.handle_event(callback); self.assertEqual(self.dialog.axis, 'X')
        self.dialog.distance.setValue(-37.25); self.dialog.move((110, 100))
        self.assertEqual(self.dialog.distance.value(), -37.25)
        self.assertFalse(self.dialog.closed)
    def test_error_during_hover_removes_preview_without_model_change(self):
        self.anchor()
        def broken_pick(position):
            raise RuntimeError('Expected view failure fixture')
        view.pick = broken_pick
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
    def test_reentry_closes_previous_session(self):
        gui._workbench_magnetic_move_dialog = self.dialog
        module.MagneticMove().Activated()
        replacement = gui._workbench_magnetic_move_dialog
        self.assertTrue(self.dialog.closed); self.assertEqual(len(view.callbacks), 1)
        replacement.close(); self.assertEqual(view.callbacks, [])
if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1] / 'DIYWorkbenchTools' / 'WorkbenchMagneticMove.py'
    assert path.exists(), 'Magnetic Move session is not implemented'
    import WorkbenchMagneticMove as module
    # Visibility is view-provider state; headless FreeCAD has no ViewObjects.
    module._visible = lambda obj: view.visibility.get(obj.Name, True)
    unittest.main()
