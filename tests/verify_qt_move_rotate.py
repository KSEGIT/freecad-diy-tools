"""Real Qt and FreeCAD geometry; only GUI command boundaries are simulated."""
from pathlib import Path
import sys, types
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App, Part
from PySide import QtWidgets
application = QtWidgets.QApplication([])
commands, calls, warnings = {}, [], []
class Selection:
    selected = []
    def getSelection(self): return self.selected
    def clearSelection(self): self.selected = []
    def addSelection(self, part): self.selected.append(part)
gui = types.ModuleType('FreeCADGui')
gui.Selection = Selection()
gui.getMainWindow = lambda: None
gui.addCommand = lambda name, command: commands.update({name: command})
gui.runCommand = lambda *args: calls.append(args)
sys.modules['FreeCADGui'] = gui
QtWidgets.QMessageBox.warning = lambda *args: warnings.append(args[-1])
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'DIYWorkbenchTools'))
import WorkbenchMoveRotate as module
assert {'DIY_MovePart', 'DIY_RotatePart'} <= commands.keys()
doc = App.newDocument('MoveRotateCheck')
doc.UndoMode = 1
piece = doc.addObject('Part::Box', 'Piece')
piece.Length, piece.Width, piece.Height = 700, 94, 44
piece.Placement.Base = App.Vector(150, 250, 350)
doc.recompute()
assert commands['DIY_MovePart'].IsActive()
gui.Selection.selected = []
commands['DIY_MovePart'].Activated()
assert warnings and not calls
class Previous:
    closed = False
    def close(self): self.closed = True
previous = Previous()
gui._workbench_place_edit_dialog = previous
gui.Selection.selected = [piece]
prefs = App.ParamGet('User parameter:BaseApp/History/Dragger')
prior_angle = prefs.GetFloat('LastRotationIncrement', 5)
prior_step = prefs.GetFloat('LastTranslationIncrement', 1)
try:
    prefs.SetFloat('LastRotationIncrement', 15)
    prefs.SetFloat('LastTranslationIncrement', 2)
    commands['DIY_MovePart'].Activated()
    assert previous.closed and calls == [('Std_TransformManip', 0)]
    assert gui.Selection.selected == [piece]
    assert prefs.GetFloat('LastRotationIncrement') == 15
    assert prefs.GetFloat('LastTranslationIncrement') == 2
finally:
    prefs.SetFloat('LastRotationIncrement', prior_angle)
    prefs.SetFloat('LastTranslationIncrement', prior_step)
commands['DIY_RotatePart'].Activated()
dialog = gui._workbench_rotate_dialog
assert dialog.angle.value() == 90
center = piece.Shape.CenterOfMass
before = piece.Placement
for axis in range(3):
    dialog.axis.setCurrentIndex(axis)
    dialog.angle.setValue(30)
    dialog.rotate()
    assert (piece.Shape.CenterOfMass - center).Length < 1e-7
assert float(piece.Length) == 700
after = piece.Placement
doc.undo(); doc.recompute()
assert (piece.Shape.CenterOfMass - center).Length < 1e-7
assert abs(piece.Placement.Rotation.Angle - after.Rotation.Angle) > 1e-5
dialog.close()
assert gui._workbench_rotate_dialog is None
commands['DIY_RotatePart'].Activated()
dialog = gui._workbench_rotate_dialog
assert dialog is not None
# Removal while open must show a useful error, not mutate a stale object.
doc.removeObject(piece.Name); doc.recompute()
dialog.rotate()
assert 'no longer' in dialog.status.text().lower()
dialog.close()
generic = doc.addObject('Part::Feature', 'Cylinder')
generic.Shape = Part.makeCylinder(10, 50)
generic.Placement.Base = App.Vector(90, 70, 50)
doc.recompute()
gui.Selection.selected = [generic]
commands['DIY_RotatePart'].Activated()
dialog = gui._workbench_rotate_dialog
center = generic.Shape.CenterOfMass
dialog.axis.setCurrentIndex(1)
dialog.angle.setValue(-45)
dialog.rotate()
assert (generic.Shape.CenterOfMass - center).Length < 1e-7
App.closeDocument(doc.Name)
dialog.rotate()
assert 'no longer' in dialog.status.text().lower()
dialog.close()
assert not commands['DIY_MovePart'].IsActive()
print('Move/rotate registration, selection errors, native command boundary, settings preservation, centre rotation on all axes, Undo, close/reopen and removed-part checks passed. No rendered GUI verification.')
