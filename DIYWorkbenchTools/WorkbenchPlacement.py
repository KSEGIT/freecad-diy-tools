"""Corner alignment and rotation commands for independent workbench boxes."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui

ICON = str(Path(__file__).with_name('WorkbenchParts.svg'))


def nearest_corner(points, clicked):
    return min(points, key=lambda p: p.distanceToPoint(clicked))


def selected_piece():
    selected = Gui.Selection.getSelection()
    if len(selected) != 1:
        raise ValueError('Select ONE solid part in the model tree first.')
    part = selected[0]
    if not hasattr(part, 'Shape') or not hasattr(part, 'Placement') or part.Shape.isNull() or not part.Shape.Solids:
        raise ValueError('Select a solid part, not a folder or spreadsheet.')
    if part.getParentGeoFeatureGroup() is not None:
        raise ValueError('Choose an independent solid part, outside a Part or Body container.')
    return part


def notice(message):
    QtWidgets.QMessageBox.information(Gui.getMainWindow(), 'Workbench placement', str(message))


class CornerDialog(QtWidgets.QDialog):
    def __init__(self, part):
        super(CornerDialog, self).__init__(Gui.getMainWindow())
        self.part = part
        self.source = None
        self.listening = False
        self.busy = False
        self.setWindowTitle('Join corners')
        self.setMinimumWidth(390)
        layout = QtWidgets.QVBoxLayout(self)
        self.message = QtWidgets.QLabel('1. Click near the chosen corner of:\n' + part.Label)
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        layout.addWidget(QtWidgets.QLabel('Click the visible edge or face near a corner.\nThe nearest real vertex is used, with no Draft settings.\nThis aligns positions; it does not prevent overlapping parts.'))
        cancel = QtWidgets.QPushButton('Cancel / Close')
        cancel.clicked.connect(self.close)
        layout.addWidget(cancel)
        Gui.Selection.clearSelection()
        Gui.Selection.addObserver(self)
        self.listening = True

    def closeEvent(self, event):
        if self.listening:
            Gui.Selection.removeObserver(self)
            self.listening = False
        super(CornerDialog, self).closeEvent(event)

    def addSelection(self, docname, objname, subname, position):
        if self.busy or not subname:
            return
        self.busy = True
        try:
            doc = App.getDocument(docname)
            target = doc.getObject(objname)
            if doc != self.part.Document or target is None or not hasattr(target, 'Shape') or target.Shape.isNull():
                raise ValueError('Click a solid piece in the same document.')
            if target.getParentGeoFeatureGroup() is not None:
                raise ValueError('Nested Part/Body targets are not supported. Use the independent pieces in this model.')
            if self.source is None and target != self.part:
                raise ValueError('First click a corner on ' + self.part.Label)
            if self.source is not None and target == self.part:
                raise ValueError('Now click a corner on a DIFFERENT piece.')
            if subname.startswith('Vertex'):
                corner = target.Shape.getElement(subname).Point
            else:
                corner = nearest_corner([v.Point for v in target.Shape.Vertexes], App.Vector(position))
            if self.source is None:
                self.source = App.Vector(corner)
                self.message.setText('2. Click near the destination corner on another piece.\nSelected source corner: {:.2f}, {:.2f}, {:.2f} mm'.format(corner.x, corner.y, corner.z))
                QtCore.QTimer.singleShot(0, Gui.Selection.clearSelection)
                return
            delta = corner - self.source
            doc.openTransaction('Join timber corners')
            try:
                placement = self.part.Placement
                placement.Base = placement.Base + delta
                self.part.Placement = placement
                doc.recompute()
                doc.commitTransaction()
            except Exception:
                doc.abortTransaction()
                raise
            self.message.setText('Corners aligned exactly. Close this window.\nUse Undo to reverse the move.')
            Gui.Selection.removeObserver(self)
            self.listening = False
            QtCore.QTimer.singleShot(0, self.select_result)
        except Exception as error:
            self.message.setText(str(error))
        finally:
            self.busy = False

    def select_result(self):
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(self.part)


class JoinCorners:
    def GetResources(self):
        return {'Pixmap': str(Path(__file__).with_name('WorkbenchJoin.svg')), 'MenuText': 'Join corners', 'ToolTip': 'Select a new piece, click its corner, then a target corner'}
    def IsActive(self):
        return App.ActiveDocument is not None
    def Activated(self):
        try:
            part = selected_piece()
            previous = getattr(Gui, '_workbench_corner_dialog', None)
            if previous is not None:
                previous.close()
            Gui._workbench_corner_dialog = CornerDialog(part)
            Gui._workbench_corner_dialog.show()
        except Exception as error:
            notice(error)


class RotatePiece:
    def __init__(self, axis=None):
        self.axis = axis
    def GetResources(self):
        label = 'Stand upright' if self.axis is None else 'Rotate {} 90 degrees'.format(self.axis)
        return {'Pixmap': str(Path(__file__).with_name('WorkbenchUpright.svg' if self.axis is None else 'WorkbenchRotate' + self.axis + '.svg')), 'MenuText': label, 'ToolTip': label + ' — select one solid part first'}
    def IsActive(self):
        return App.ActiveDocument is not None
    def Activated(self):
        try:
            part = selected_piece()
            previous = getattr(Gui, '_workbench_corner_dialog', None)
            if previous is not None:
                previous.close()
            placement = part.Placement
            old = part.Shape.BoundBox
            low = App.Vector(old.XMin, old.YMin, old.ZMin)
            center = old.Center
            if self.axis is None:
                if part.TypeId == 'Part::Box':
                    sizes = [float(part.Length), float(part.Width), float(part.Height)]
                else:
                    shape = part.Shape.copy()
                    shape.Placement = placement.inverse().multiply(shape.Placement)
                    bounds = shape.BoundBox
                    sizes = [bounds.XLength, bounds.YLength, bounds.ZLength]
                index = max(range(3), key=lambda i: sizes[i])
                directions = [App.Vector(1,0,0), App.Vector(0,1,0), App.Vector(0,0,1)]
                current = placement.Rotation.multVec(directions[index])
                rotation = App.Rotation(current, App.Vector(0,0,1))
            else:
                directions = {'X': App.Vector(1,0,0), 'Y': App.Vector(0,1,0), 'Z': App.Vector(0,0,1)}
                rotation = App.Rotation(directions[self.axis], 90)
            doc = part.Document
            doc.openTransaction('Orient workbench piece')
            try:
                placement.Base = center + rotation.multVec(placement.Base - center)
                placement.Rotation = rotation.multiply(placement.Rotation)
                part.Placement = placement
                doc.recompute()
                if self.axis is None:
                    new = part.Shape.BoundBox
                    placement = part.Placement
                    placement.Base = placement.Base + low - App.Vector(new.XMin, new.YMin, new.ZMin)
                    part.Placement = placement
                    doc.recompute()
                doc.commitTransaction()
            except Exception:
                doc.abortTransaction()
                raise
        except Exception as error:
            notice(error)


Gui.addCommand('DIY_JoinCorners', JoinCorners())
Gui.addCommand('DIY_StandUpright', RotatePiece())
for axis in ('X', 'Y', 'Z'):
    Gui.addCommand('DIY_Rotate' + axis, RotatePiece(axis))
