from pathlib import Path
import os, sys, types, importlib.util
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App, Part
from PySide import QtWidgets
from pivy import coin
application=QtWidgets.QApplication([])
scene=coin.SoSeparator()
class Selection:
 def clearSelection(self): pass
 def addSelection(self,*args): pass
 def addObserver(self,*args): pass
 def removeObserver(self,*args): pass
class View:
 def getSceneGraph(self): return scene
class GuiDoc:
 def activeView(self): return View()
gui=types.ModuleType('FreeCADGui')
gui.getMainWindow=lambda:None
gui.activeDocument=lambda:GuiDoc()
gui.Selection=Selection()
gui.addCommand=lambda *args:None
gui.runCommand=lambda *args:None
sys.modules['FreeCADGui']=gui
helper=types.ModuleType('WorkbenchPlacement')
helper.selected_piece=lambda:piece
sys.modules['WorkbenchPlacement']=helper
spec=importlib.util.spec_from_file_location('place_edit',str(Path(__file__).resolve().parents[1] / 'DIYWorkbenchTools' / 'WorkbenchPlaceEdit.py'))
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
doc=App.newDocument('WidgetCheck')
piece=doc.addObject('Part::Box','Piece'); piece.Length=1700; piece.Width=94; piece.Height=44
piece.addProperty('App::PropertyString','CutAxis'); piece.CutAxis='X'; doc.recompute()
dialog=module.PlaceEditDialog(piece); gui._workbench_place_edit_dialog=dialog
assert scene.getNumChildren()==1
assert dialog.axis==0
assert '1700' in dialog.dimensions.text()
dialog.length.setValue(800); dialog.cut(); assert float(piece.Length)==800
dialog.length.setValue(30); dialog.cut(); assert float(piece.Length)==30
center=piece.Shape.CenterOfMass
dialog.angle.setValue(90); dialog.rotation_axis.setCurrentIndex(1); dialog.rotate()
assert (piece.Shape.CenterOfMass-center).Length<1e-7
assert float(piece.Length)==30
other=doc.addObject('Part::Box','Target'); other.Length=600; other.Width=94; other.Height=44; other.Placement.Base=App.Vector(1000,0,0); doc.recompute()
dialog.start_faces()
dialog.addSelection(doc.Name,piece.Name,'Face1',(0,0,0))
assert dialog.source=='Face1'
dialog.addSelection(doc.Name,other.Name,'Face2',(0,0,0))
assert not dialog.listening
assert (piece.Shape.Faces[0].CenterOfMass-other.Shape.Faces[1].CenterOfMass).Length<1e-6
dialog.close(); assert scene.getNumChildren()==0; assert gui._workbench_place_edit_dialog is None
# Reopen a short piece; CutAxis must stay X despite Width now being longest.
dialog=module.PlaceEditDialog(piece); assert dialog.axis==0; dialog.close()
generic=doc.addObject('Part::Feature','Cylinder')
generic.Shape=Part.makeCylinder(10,60)
generic.Placement=App.Placement(App.Vector(50,100,200),App.Rotation(App.Vector(0,1,0),35))
doc.recompute()
dialog=module.PlaceEditDialog(generic)
assert not dialog.length.isEnabled()
assert dialog.mouse_angle.value()==90
assert dialog.angle.value()==90
assert dialog.mouse_step.value()==1
sizes,origin=module.local_dimensions(generic)
assert max(abs(a-b) for a,b in zip(sizes,[20,20,60]))<1e-7
prefs=App.ParamGet('User parameter:BaseApp/History/Dragger')
prior_angle=prefs.GetFloat('LastRotationIncrement',5)
prior_step=prefs.GetFloat('LastTranslationIncrement',1)
calls=[]
gui.runCommand=lambda *args:calls.append(args)
dialog.mouse_move()
assert prefs.GetFloat('LastRotationIncrement')==90
assert prefs.GetFloat('LastTranslationIncrement')==1
assert calls==[('Std_TransformManip',0)]
prefs.SetFloat('LastRotationIncrement',prior_angle)
prefs.SetFloat('LastTranslationIncrement',prior_step)
assert scene.getNumChildren()==0
App.closeDocument(doc.Name)
print('Real Qt editor, resize, rotate, face clicks, cleanup, reopen, generic solid and mouse rotation step checks passed. GUI view is simulated; no rendered screenshot check.')
