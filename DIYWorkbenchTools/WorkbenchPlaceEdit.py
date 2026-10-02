"""Modeless placement and cut-length editor for independent solid pieces."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
import Part
from pivy import coin
from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui
from WorkbenchPlacement import selected_piece

DIMS = ('Length', 'Width', 'Height')
AXES = (App.Vector(1, 0, 0), App.Vector(0, 1, 0), App.Vector(0, 0, 1))


def local_dimensions(part):
    """Read box cut sizes or the bounding dimensions in a solid's own frame."""
    if part.TypeId == 'Part::Box':
        return [float(getattr(part, name)) for name in DIMS], App.Vector()
    shape = part.Shape.copy()
    shape.Placement = part.Placement.inverse().multiply(shape.Placement)
    bounds = shape.BoundBox
    return [bounds.XLength, bounds.YLength, bounds.ZLength], App.Vector(bounds.XMin, bounds.YMin, bounds.ZMin)


def rotated_placement(placement, rotation, center):
    """Rotate a placement around a world-space point without changing geometry."""
    return App.Placement(center + rotation.multVec(placement.Base - center),
                         rotation.multiply(placement.Rotation))


def face_geometry(face):
    if not isinstance(face.Surface, Part.Plane):
        raise ValueError('Choose a planar face.')
    u0, u1, v0, v1 = face.ParameterRange
    # FreeCAD 1.1 normalAt calls Tools::getNormal, including face Orientation.
    normal = face.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    normal.normalize()
    return face.CenterOfMass, normal


def face_placement(placement, source, target, gap, auto_rotate):
    source_center, source_normal = face_geometry(source)
    target_center, target_normal = face_geometry(target)
    rotation = App.Rotation(source_normal, -target_normal) if auto_rotate else App.Rotation()
    result = rotated_placement(placement, rotation, source_center)
    result.Base = result.Base + target_center + target_normal * gap - source_center
    return result


class PlaceEditDialog(QtWidgets.QDialog):
    def __init__(self, part):
        super(PlaceEditDialog, self).__init__(Gui.getMainWindow())
        self.part, self.doc = part, part.Document
        self.docname, self.objname = self.doc.Name, part.Name
        self.can_cut = part.TypeId == 'Part::Box'
        sizes, _ = local_dimensions(part)
        saved_axis = str(getattr(part, 'CutAxis', ''))
        self.axis = ('XYZ'.index(saved_axis) if saved_axis in ('X', 'Y', 'Z') else
                     max(range(3), key=lambda i: sizes[i]))
        self.source = None
        self.listening = self.busy = self.closed = False
        self.setWindowTitle('Place & edit — ' + part.Label)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setMinimumWidth(380)
        layout = QtWidgets.QVBoxLayout(self)
        self.dimensions = QtWidgets.QLabel()
        self.orientation = QtWidgets.QLabel()
        self.orientation.setWordWrap(True)
        layout.addWidget(self.dimensions)
        layout.addWidget(self.orientation)
        form = QtWidgets.QFormLayout()
        layout.addLayout(form)
        self.length = self.spin(0.01, 10000000, 1, ' mm')
        self.step = self.spin(0.01, 100000, 1, ' mm')
        self.step.setValue(1)
        self.step.valueChanged.connect(self.length.setSingleStep)
        self.cut_axis = QtWidgets.QComboBox()
        self.cut_axis.addItems(['X / Length', 'Y / Width', 'Z / Height'])
        self.cut_axis.setCurrentIndex(self.axis)
        form.addRow('Cut dimension (local)', self.cut_axis)
        form.addRow('Cut length', self.length)
        form.addRow('+ / − step', self.step)
        cut_button = self.button(layout, 'Apply cut length', self.cut)
        for widget in (self.length, self.step, self.cut_axis, cut_button):
            widget.setEnabled(self.can_cut)
        if not self.can_cut:
            layout.addWidget(QtWidgets.QLabel('Cut length requires an editable box. This solid can be moved, rotated or stuck to a face.'))
        self.angle = self.spin(-360, 360, 90, '°')
        self.angle.setValue(90)
        self.rotation_axis = QtWidgets.QComboBox()
        self.rotation_axis.addItems(['X', 'Y', 'Z'])
        form.addRow('Rotate by', self.angle)
        form.addRow('World axis', self.rotation_axis)
        self.button(layout, 'Apply rotation about piece centre', self.rotate)
        self.position = [self.spin(-10000000, 10000000, 1, ' mm') for _ in range(3)]
        for axis, spin in zip('XYZ', self.position):
            form.addRow('Position ' + axis, spin)
        self.button(layout, 'Apply position', self.move)
        self.mouse_angle = self.spin(0.01, 360, 90, '°')
        self.mouse_angle.setValue(90)
        self.mouse_step = self.spin(0.01, 100000, 1, ' mm')
        self.mouse_step.setValue(1)
        form.addRow('Mouse rotation step', self.mouse_angle)
        form.addRow('Mouse move step', self.mouse_step)
        self.button(layout, 'Move / rotate with mouse', self.mouse_move)
        self.gap = self.spin(-100000, 100000, 1, ' mm')
        form.addRow('Face gap', self.gap)
        self.auto_rotate = QtWidgets.QCheckBox('Rotate source face to face target')
        self.auto_rotate.setChecked(True)
        layout.addWidget(self.auto_rotate)
        self.button(layout, 'Stick faces: choose source then target', self.start_faces)
        self.status = QtWidgets.QLabel('Each Apply has its own Undo step.\nFace sticking centres faces; parts can overlap.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.button(layout, 'Close', self.close)
        self.scene = Gui.activeDocument().activeView().getSceneGraph()
        self.guide = coin.SoSeparator()
        pick = coin.SoPickStyle()
        pick.style.setValue(coin.SoPickStyle.UNPICKABLE)
        self.guide.addChild(pick)
        colour = coin.SoBaseColor()
        colour.rgb.setValue(0.1, 1.0, 0.2)
        self.guide.addChild(colour)
        draw = coin.SoDrawStyle()
        draw.lineWidth.setValue(3)
        self.guide.addChild(draw)
        self.points = coin.SoCoordinate3()
        self.guide.addChild(self.points)
        lines = coin.SoLineSet()
        lines.numVertices.setValues(0, [2, 2, 2, 2, 2])
        self.guide.addChild(lines)
        self.text_position = coin.SoTranslation()
        self.guide.addChild(self.text_position)
        font = coin.SoFont()
        font.size.setValue(16)
        self.guide.addChild(font)
        self.text = coin.SoText2()
        self.guide.addChild(self.text)
        self.scene.addChild(self.guide)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.refresh)
        App.addDocumentObserver(self)
        self.refresh(force=True)
        if not self.closed:
            self.cut_axis.currentIndexChanged.connect(self.change_axis)
            self.timer.start(350)

    @staticmethod
    def spin(low, high, step, suffix):
        widget = QtWidgets.QDoubleSpinBox()
        widget.setDecimals(2)
        widget.setRange(low, high)
        widget.setSingleStep(step)
        widget.setSuffix(suffix)
        return widget

    @staticmethod
    def button(layout, text, callback):
        button = QtWidgets.QPushButton(text)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def report(self, error):
        self.status.setText(str(error))
        App.Console.PrintError('Place & edit: {}\n'.format(error))

    def valid(self):
        return (App.getDocument(self.docname) is self.doc and
                self.doc.getObject(self.objname) is self.part)

    def transaction(self, label, operation):
        try:
            if not self.valid():
                raise ValueError('The document or piece has been closed or removed.')
            self.stop_faces()
            self.doc.openTransaction(label)
            try:
                operation()
                self.doc.recompute()
                self.doc.commitTransaction()
            except Exception:
                self.doc.abortTransaction()
                raise
            self.refresh(force=True)
            self.status.setText(label + '. Use Undo to reverse it.')
        except Exception as error:
            self.report(error)

    def change_axis(self, index):
        self.axis = index
        self.length.setValue(float(getattr(self.part, DIMS[self.axis])))
        self._state = None
        self.refresh()
        self.status.setText('Cut dimension changed. Apply cut length to save it for this piece.')

    def cut(self):
        if not self.can_cut:
            self.report('Cut length requires an editable Part::Box.')
            return
        def apply():
            if 'CutAxis' not in self.part.PropertiesList:
                self.part.addProperty('App::PropertyEnumeration', 'CutAxis', 'Stock',
                                      'Local dimension used for the cut length')
                self.part.CutAxis = ['X', 'Y', 'Z']
            self.part.CutAxis = 'XYZ'[self.axis]
            setattr(self.part, DIMS[self.axis], self.length.value())
        self.transaction('Change cut length', apply)

    def rotate(self):
        rotation = App.Rotation(AXES[self.rotation_axis.currentIndex()], self.angle.value())
        self.transaction('Rotate piece', lambda: setattr(self.part, 'Placement',
                         rotated_placement(self.part.Placement, rotation, self.part.Shape.CenterOfMass)))

    def move(self):
        def apply():
            placement = self.part.Placement
            placement.Base = App.Vector(*(spin.value() for spin in self.position))
            self.part.Placement = placement
        self.transaction('Move piece', apply)

    def mouse_move(self):
        try:
            if not self.valid() or App.ActiveDocument is not self.doc:
                raise ValueError('Activate the piece document first.')
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(self.part)
            preferences = App.ParamGet('User parameter:BaseApp/History/Dragger')
            preferences.SetFloat('LastRotationIncrement', self.mouse_angle.value())
            preferences.SetFloat('LastTranslationIncrement', self.mouse_step.value())
            self.close()
            Gui.runCommand('Std_TransformManip', 0)
        except Exception as error:
            App.Console.PrintError('Place & edit: {}\n'.format(error))
            QtWidgets.QMessageBox.warning(Gui.getMainWindow(), 'Place & edit', str(error))

    def stop_faces(self):
        if self.listening:
            Gui.Selection.removeObserver(self)
            self.listening = False
        self.source = None

    def start_faces(self):
        self.stop_faces()
        Gui.Selection.clearSelection()
        Gui.Selection.addObserver(self)
        self.listening = True
        self.status.setText('1. Click a planar source face on ' + self.part.Label)

    def addSelection(self, docname, objname, subname, position):
        if not self.listening or self.busy:
            return
        self.busy = True
        try:
            if not self.valid() or docname != self.docname:
                raise ValueError('Choose a face in the piece document.')
            obj = self.doc.getObject(objname)
            if obj is None or obj.getParentGeoFeatureGroup() is not None:
                raise ValueError('Choose an independent object outside a Part or Body.')
            if not subname.startswith('Face') or not subname[4:].isdigit():
                raise ValueError('Click a planar face, not an edge or vertex.')
            face = obj.Shape.getElement(subname)
            face_geometry(face)
            if self.source is None:
                if obj is not self.part:
                    raise ValueError('Choose the source face on ' + self.part.Label + ' first.')
                self.source = subname
                self.status.setText('2. Click a target face on a DIFFERENT object.')
                QtCore.QTimer.singleShot(0, Gui.Selection.clearSelection)
            else:
                if obj is self.part:
                    raise ValueError('Choose a target face on a DIFFERENT object.')
                source = self.part.Shape.getElement(self.source)
                placement = face_placement(self.part.Placement, source, face,
                                           self.gap.value(), self.auto_rotate.isChecked())
                self.transaction('Stick faces', lambda: setattr(self.part, 'Placement', placement))
        except Exception as error:
            self.report(error)
        finally:
            self.busy = False

    def refresh(self, force=False):
        if self.closed:
            return
        try:
            if not self.valid():
                self.close()
                return
            sizes, origin = local_dimensions(self.part)
            placement = self.part.Placement
            state = tuple(sizes) + tuple(origin) + tuple(placement.Base) + tuple(placement.Rotation.Q)
            if not force and state == getattr(self, '_state', None):
                return
            self._state = state
            label = 'Length × width × height' if self.can_cut else 'Local bounding size X × Y × Z'
            self.dimensions.setText((label + ': {:.2f} × {:.2f} × {:.2f} mm').format(*sizes))
            yaw, pitch, roll = placement.Rotation.toEuler()
            self.orientation.setText('Current yaw Z / pitch Y / roll X: {:.2f}° / {:.2f}° / {:.2f}°'.format(yaw, pitch, roll))
            for spin, value in [(self.length, sizes[self.axis])] + list(zip(self.position, placement.Base)):
                if force or not spin.hasFocus():
                    spin.setValue(value)
            # Offset guide from the stock; end ticks and extension lines mark its length.
            side = (self.axis + 1) % 3
            start = origin
            end = origin + AXES[self.axis] * sizes[self.axis]
            offset = AXES[side] * (-max(15, min(sizes) * 0.3))
            a, b = start + offset, end + offset
            tick = AXES[side] * 4
            points = [a, b, start, a, end, b, a - tick, a + tick, b - tick, b + tick]
            self.points.point.setValues(0, [tuple(placement.multVec(p)) for p in points])
            self.text_position.translation.setValue(tuple(placement.multVec((a + b) * 0.5 + offset * 0.3)))
            self.text.string.setValue(('Cut' if self.can_cut else 'Size') +
                                      ' {:.2f} mm (local {})'.format(sizes[self.axis], 'XYZ'[self.axis]))
        except Exception as error:
            self.report(error)
            self.close()

    def slotDeletedDocument(self, doc):
        if doc is self.doc:
            self.close()

    def closeEvent(self, event):
        if not self.closed:
            self.closed = True
            if getattr(Gui, '_workbench_place_edit_dialog', None) is self:
                Gui._workbench_place_edit_dialog = None
            self.timer.stop()
            self.stop_faces()
            App.removeDocumentObserver(self)
            try:
                if self.scene.findChild(self.guide) >= 0:
                    self.scene.removeChild(self.guide)
            except Exception as error:
                App.Console.PrintError('Place & edit guide cleanup: {}\n'.format(error))
        super(PlaceEditDialog, self).closeEvent(event)


class PlaceEdit:
    def GetResources(self):
        return {'Pixmap': str(Path(__file__).with_name('WorkbenchPlaceEdit.svg')),
                'MenuText': 'Place & edit', 'ToolTip': 'Edit cut length, move, rotate or stick two faces'}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            part = selected_piece()
            previous = getattr(Gui, '_workbench_place_edit_dialog', None)
            if previous is not None:
                previous.close()
            Gui._workbench_place_edit_dialog = PlaceEditDialog(part)
            Gui._workbench_place_edit_dialog.show()
        except Exception as error:
            App.Console.PrintError('Place & edit: {}\n'.format(error))
            QtWidgets.QMessageBox.warning(Gui.getMainWindow(), 'Place & edit', str(error))


Gui.addCommand('DIY_PlaceEdit', PlaceEdit())
