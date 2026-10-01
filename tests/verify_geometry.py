import ast
from pathlib import Path
import sys
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App, Part
path = Path(__file__).resolve().parents[1] / 'DIYWorkbenchTools' / 'WorkbenchPlaceEdit.py'
tree = ast.parse(path.read_text())
functions = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('rotated_placement', 'face_placement', 'face_geometry')], type_ignores=[])
scope = {'App': App, 'Part': Part}
exec(compile(functions, str(path), 'exec'), scope)
def same(a,b):
    assert (a-b).Length < 1e-7, (a,b)
p = App.Placement(App.Vector(10,20,30), App.Rotation(App.Vector(0,0,1), 30))
center = p.multVec(App.Vector(50,10,5))
r = App.Rotation(App.Vector(0,1,0),90)
q = scope['rotated_placement'](p,r,center)
same(q.multVec(App.Vector(50,10,5)), center)
b = Part.makeBox(100,20,10)
source = b.Faces[0]
target = b.Faces[1]
normal = scope['face_geometry'](source)[1]
same(normal,App.Vector(-1,0,0))
for auto in (False,True):
    q = scope['face_placement'](App.Placement(), source,target,7,auto)
    same(q.multVec(source.CenterOfMass),target.CenterOfMass + App.Vector(7,0,0))
    if auto:
        same(q.Rotation.multVec(normal),App.Vector(-1,0,0))
# Orthogonal normals exercise rotation and displacement together.
q = scope['face_placement'](App.Placement(),source,b.Faces[5],3,True)
same(q.multVec(source.CenterOfMass), b.Faces[5].CenterOfMass + App.Vector(0,0,3))
same(q.Rotation.multVec(normal),App.Vector(0,0,-1))
print('Geometry tests passed')
