"""Modeless magnetic translation with an unpickable Coin preview.

View bindings verified in official FreeCAD src/Gui/View3DPy.cpp at the
installed 1.1.3 commit 145529fe741292ff0b3977a01195bf0247425794.
"""
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
from WorkbenchMagneticGeometry import (
    shape_candidates, choose_snap, constrained_point, translated_placement,
)


def _independent(obj):
    return (obj.TypeId not in ('App::Part', 'PartDesign::Body', 'App::Link')
            and hasattr(obj, 'Shape') and hasattr(obj, 'Placement')
            and not obj.Shape.isNull() and bool(obj.Shape.Solids)
            and obj.getParentGeoFeatureGroup() is None)


def _visible(obj):
    return bool(getattr(getattr(obj, 'ViewObject', None), 'Visibility', False))


def _workbench():
    return Gui.activeWorkbench().name()


class MagneticMoveDialog(QtWidgets.QDialog):
    def __init__(self, part):
        super(MagneticMoveDialog, self).__init__(Gui.getMainWindow())
        self.part, self.doc = part, part.Document
        self.docname, self.objname = self.doc.Name, part.Name
        self.original = App.Placement(part.Placement)
        self.source_shape_hash = part.Shape.hashCode()
        self.view = Gui.activeDocument().activeView()
        self.workbench = _workbench()
        self.source = self.destination = None
        self.axis = None
        self.closed = False
        self.callback = None
        self.preview_root = None
        self.cache = {}
        self.left_down = False
        self.setWindowTitle('Magnetic Move — ' + part.Label)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setMinimumWidth(330)
        layout = QtWidgets.QVBoxLayout(self)
        self.message = QtWidgets.QLabel('Click a corner on ' + part.Label)
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        row = QtWidgets.QHBoxLayout(); layout.addLayout(row)
        self.axis_buttons = {}
        for axis in ('X', 'Y', 'Z'):
            button = QtWidgets.QPushButton(axis); button.setCheckable(True)
            button.clicked.connect(lambda checked=False, a=axis: self.set_axis(a))
            row.addWidget(button); self.axis_buttons[axis] = button
        free = QtWidgets.QPushButton('Free'); free.clicked.connect(lambda: self.set_axis(None)); row.addWidget(free)
        row = QtWidgets.QHBoxLayout(); layout.addLayout(row)
        self.distance = QtWidgets.QDoubleSpinBox()
        self.distance.setRange(-10000000, 10000000); self.distance.setDecimals(3)
        self.distance.setSuffix(' mm'); self.distance.setEnabled(False)
        row.addWidget(self.distance)
        self.apply_button = QtWidgets.QPushButton('Apply distance')
        self.apply_button.setEnabled(False); self.apply_button.clicked.connect(self.apply_distance)
        row.addWidget(self.apply_button)
        cancel = QtWidgets.QPushButton('Cancel'); cancel.clicked.connect(self.close); layout.addWidget(cancel)
        self.timer = QtCore.QTimer(self); self.timer.setInterval(100)
        self.timer.timeout.connect(self.check_context)
        try:
            self.make_preview()
            self.callback = self.view.addEventCallbackPivy(coin.SoEvent.getClassTypeId(), self.handle_event)
            Gui.Selection.clearSelection()
            self.timer.start()
        except Exception:
            self.cleanup()
            raise

    def make_preview(self):
        self.scene = self.view.getSceneGraph()
        root = coin.SoSeparator(); self.preview_root = root
        pick = coin.SoPickStyle(); pick.style = coin.SoPickStyle.UNPICKABLE; root.addChild(pick)
        self.ghost = coin.SoSeparator(); root.addChild(self.ghost)
        self.translation = coin.SoTranslation(); self.ghost.addChild(self.translation)
        material = coin.SoMaterial(); material.diffuseColor = (0.25, 0.7, 0.95); material.transparency = 0.7
        self.ghost.addChild(material)
        vertices, triangles = self.part.Shape.tessellate(1.0)
        coords = coin.SoCoordinate3(); coords.point.setValues(0, len(vertices), [tuple(v) for v in vertices])
        self.ghost.addChild(coords)
        faces = coin.SoIndexedFaceSet(); indices = [i for triangle in triangles for i in (*triangle, -1)]
        faces.coordIndex.setValues(0, len(indices), indices); self.ghost.addChild(faces)
        self.ghost_switch = coin.SoSwitch(); self.ghost_switch.whichChild = coin.SO_SWITCH_NONE
        root.removeChild(self.ghost); self.ghost_switch.addChild(self.ghost); root.addChild(self.ghost_switch)
        guides = coin.SoSeparator(); root.addChild(guides)
        material = coin.SoMaterial(); material.diffuseColor = (0.2, 1., 0.35); guides.addChild(material)
        draw = coin.SoDrawStyle(); draw.lineWidth = 2; draw.pointSize = 9; guides.addChild(draw)
        self.guide_coords = coin.SoCoordinate3(); guides.addChild(self.guide_coords)
        self.lines = coin.SoLineSet(); guides.addChild(self.lines)
        self.marker_coords = coin.SoCoordinate3(); guides.addChild(self.marker_coords)
        self.marker = coin.SoPointSet(); self.marker.numPoints = 0; guides.addChild(self.marker)
        self.scene.addChild(root)

    def valid_context(self):
        try:
            return (App.ActiveDocument is self.doc and App.getDocument(self.docname) is self.doc
                    and self.doc.getObject(self.objname) is self.part
                    and Gui.activeDocument().activeView() == self.view
                    and _workbench() == self.workbench
                    and self.part.Placement == self.original
                    and self.part.Shape.hashCode() == self.source_shape_hash)
        except Exception:
            return False

    def check_context(self):
        if not self.closed and not self.valid_context():
            self.close()

    def targets(self):
        """Cache geometry by shape identity while rechecking visibility each move."""
        candidates = []; present = set(); self.candidate_objects = {}
        for obj in self.doc.Objects:
            if obj is self.part or not _independent(obj) or not _visible(obj):
                continue
            present.add(obj.Name)
            key = (obj.Shape.hashCode(), str(obj.Placement), obj.Label)
            cached = self.cache.get(obj.Name)
            if cached is None or cached[0] != key:
                cached = (key, shape_candidates(obj.Shape, obj.Label)); self.cache[obj.Name] = cached
            candidates.extend(cached[1])
            self.candidate_objects.update((id(candidate), obj) for candidate in cached[1])
        for name in list(self.cache):
            if name not in present:
                del self.cache[name]
        return candidates

    def visible_candidates(self, position):
        """Reject obscured points using the feature picked at each nearby pixel."""
        result = []
        for candidate in self.targets():
            pixel = self.view.getPointOnScreen(candidate[1])
            if (pixel[0] - position[0]) ** 2 + (pixel[1] - position[1]) ** 2 > 14 ** 2:
                continue
            obj, info = self.picked(pixel)
            if obj is not self.candidate_objects[id(candidate)]:
                continue
            component = info.get('Component', '')
            if not component.startswith(('Vertex', 'Edge', 'Face')):
                continue
            feature = obj.Shape.getElement(component)
            # Test membership in the visible picked feature, avoiding the depth
            # ambiguity of front and rear corners at the same screen pixel.
            if feature.distToShape(Part.Vertex(candidate[1]))[0] < 1e-6:
                result.append(candidate)
        return result

    def picked(self, position):
        info = self.view.getObjectInfo(tuple(int(v) for v in position))
        if not info or info.get('Document') != self.docname or 'ParentObject' in info:
            return None, None
        obj = self.doc.getObject(info.get('Object', ''))
        if obj is None or not _independent(obj):
            return None, None
        return obj, info

    def point_on_plane(self, position):
        """Intersect the camera ray with a plane through the chosen source."""
        width, height = self.view.getSize()
        camera = self.view.getCameraNode()
        volume = camera.getViewVolume(float(width) / max(1, height))
        near, far = volume.projectPointToLine(coin.SbVec2f(float(position[0]) / max(1, width),
                                                        float(position[1]) / max(1, height)))
        origin, direction = App.Vector(tuple(near)), App.Vector(tuple(far)) - App.Vector(tuple(near))
        normal = App.Vector(tuple(camera.orientation.getValue().multVec(coin.SbVec3f(0, 0, -1))))
        divisor = direction.dot(normal)
        if abs(divisor) < 1e-12:
            return App.Vector(self.source)
        return origin + direction * ((self.source - origin).dot(normal) / divisor)

    def axis_point(self, position, plane_point):
        if self.axis is None:
            return plane_point
        # A world axis viewed end-on has no cursor distance. Keep the current
        # distance; the signed distance field remains available in this view.
        axis = App.Vector(*(1 if a == self.axis else 0 for a in 'XYZ'))
        start = self.view.getPointOnScreen(self.source)
        end = self.view.getPointOnScreen(self.source + axis * 100)
        dx, dy = end[0] - start[0], end[1] - start[1]
        square = dx * dx + dy * dy
        if square < 1e-6:
            return constrained_point(self.destination or self.source, self.source, self.axis)
        # Ray/axis closest approach provides correct perspective movement.
        width, height = self.view.getSize(); camera = self.view.getCameraNode()
        near, far = camera.getViewVolume(float(width) / max(1, height)).projectPointToLine(
            coin.SbVec2f(float(position[0]) / max(1, width), float(position[1]) / max(1, height)))
        ray = App.Vector(tuple(far)) - App.Vector(tuple(near)); ray.normalize()
        offset = App.Vector(tuple(near)) - self.source
        cosine = axis.dot(ray); denominator = 1 - cosine * cosine
        if denominator < 1e-10:
            return constrained_point(self.destination or self.source, self.source, self.axis)
        distance = (axis.dot(offset) - cosine * ray.dot(offset)) / denominator
        return self.source + axis * distance

    def move(self, position):
        if self.closed or self.source is None:
            return
        snap = choose_snap(self.visible_candidates(position), position, self.view.getPointOnScreen,
                           anchor=self.source, axis=self.axis)
        if snap is None:
            obj, info = self.picked(position)
            if obj is not None and obj is not self.part and _visible(obj):
                component = info.get('Component', '')
                if component.startswith('Face'):
                    face = obj.Shape.getElement(component)
                    if isinstance(face.Surface, Part.Plane):
                        point = App.Vector(info['x'], info['y'], info['z'])
                        snap = choose_snap([('face', point, obj.Label + ' ' + component)], position,
                                           self.view.getPointOnScreen, anchor=self.source, axis=self.axis)
        if snap is not None:
            self.preview(snap[1], snap[2] + ' — ' + snap[0])
        else:
            point = self.axis_point(position, self.point_on_plane(position))
            self.preview(point, 'Cursor' if self.axis is None else self.axis + ' axis')

    def preview(self, destination, label):
        self.destination = App.Vector(destination)
        delta = self.destination - self.source
        self.translation.translation.setValue(delta.x, delta.y, delta.z)
        self.ghost_switch.whichChild = coin.SO_SWITCH_ALL
        self.marker_coords.point.setValue(tuple(self.destination)); self.marker.numPoints = 1
        # Three world-axis steps show the delta as well as the direct travel line.
        a = self.source; b = a + App.Vector(delta.x, 0, 0); c = b + App.Vector(0, delta.y, 0)
        points = [tuple(a), tuple(b), tuple(c), tuple(self.destination), tuple(a), tuple(self.destination)]
        self.guide_coords.point.setValues(0, len(points), points); self.lines.numVertices.setValues(0, 2, [4, 2])
        self.message.setText('{}\nΔ X {:.2f}  Y {:.2f}  Z {:.2f} mm\nDistance {:.2f} mm\nClick to place. X / Y / Z lock; Esc cancels.'.format(
            label, delta.x, delta.y, delta.z, delta.Length))

    def click(self, position):
        if self.closed:
            return
        if self.source is None:
            obj, info = self.picked(position)
            if obj is not self.part:
                self.message.setText('Click a corner on ' + self.part.Label)
                return
            component = info.get('Component', '')
            if not component.startswith(('Vertex', 'Edge', 'Face')):
                return
            feature = self.part.Shape.getElement(component)
            candidates = [c for c in shape_candidates(feature, self.part.Label) if c[0] == 'vertex']
            snap = choose_snap(candidates, position, self.view.getPointOnScreen)
            if snap is None:
                self.message.setText('Click closer to a visible corner on ' + self.part.Label)
                return
            self.source = App.Vector(snap[1]); self.preview(self.source, 'Source corner chosen')
            self.set_axis(self.axis, toggle=False)
        else:
            self.move(position); self.commit()

    def set_axis(self, axis, toggle=True):
        if toggle and axis == self.axis:
            axis = None
        self.axis = axis
        for name, button in self.axis_buttons.items():
            button.setChecked(name == axis)
        enabled = axis is not None and self.source is not None
        self.distance.setEnabled(enabled); self.apply_button.setEnabled(enabled)
        if self.source is not None:
            destination = constrained_point(self.destination or self.source, self.source, axis)
            self.preview(destination, 'Free move' if axis is None else axis + ' axis')
            if axis is not None:
                self.distance.setValue(getattr(destination - self.source, axis.lower()))

    def apply_distance(self):
        if self.axis is None or self.source is None or self.closed:
            return
        axis = App.Vector(*(1 if a == self.axis else 0 for a in 'XYZ'))
        self.preview(self.source + axis * self.distance.value(), self.axis + ' exact distance')
        self.commit()

    def commit(self):
        if not self.valid_context():
            self.close(); return
        if self.source is None or self.destination is None:
            return
        self.doc.openTransaction('Magnetic Move')
        try:
            self.part.Placement = translated_placement(self.original, self.source, self.destination)
            self.doc.recompute(); self.doc.commitTransaction()
        except Exception:
            self.doc.abortTransaction(); self.close(); raise
        self.close()

    def handle_event(self, callback):
        if self.closed:
            return
        try:
            if not self.valid_context():
                self.close(); return
            event = callback.getEvent()
            if event.isOfType(coin.SoKeyboardEvent.getClassTypeId()):
                if event.getState() == coin.SoButtonEvent.DOWN:
                    key = event.getKey()
                    if key == coin.SoKeyboardEvent.ESCAPE:
                        callback.setHandled(); self.close()
                    else:
                        for axis in 'XYZ':
                            if key == getattr(coin.SoKeyboardEvent, axis):
                                callback.setHandled(); self.set_axis(axis)
                return
            if event.isOfType(coin.SoMouseButtonEvent.getClassTypeId()):
                if event.getButton() != coin.SoMouseButtonEvent.BUTTON1:
                    return
                if event.wasCtrlDown() or event.wasAltDown() or event.wasShiftDown():
                    return
                callback.setHandled()
                if event.getState() == coin.SoButtonEvent.DOWN:
                    self.left_down = True; self.click(tuple(event.getPosition().getValue()))
                else:
                    self.left_down = False
            elif event.isOfType(coin.SoLocation2Event.getClassTypeId()):
                if not event.wasCtrlDown() and not event.wasAltDown() and not event.wasShiftDown():
                    self.move(tuple(event.getPosition().getValue()))
        except Exception as error:
            App.Console.PrintError('Magnetic Move: ' + str(error) + '\n')
            self.close()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close(); event.accept()
        elif event.key() in (QtCore.Qt.Key_X, QtCore.Qt.Key_Y, QtCore.Qt.Key_Z):
            self.set_axis(chr(event.key())); event.accept()
        else:
            super(MagneticMoveDialog, self).keyPressEvent(event)

    def cleanup(self):
        if self.closed:
            return
        self.closed = True
        self.timer.stop()
        if self.callback is not None:
            callback, self.callback = self.callback, None
            try:
                self.view.removeEventCallbackPivy(coin.SoEvent.getClassTypeId(), callback)
            except (RuntimeError, ReferenceError):
                # A destroyed native view has already released its callbacks.
                pass
        if self.preview_root is not None:
            root, self.preview_root = self.preview_root, None
            self.scene.removeChild(root)
        if getattr(Gui, '_workbench_magnetic_move_dialog', None) is self:
            Gui._workbench_magnetic_move_dialog = None

    def closeEvent(self, event):
        self.cleanup()
        super(MagneticMoveDialog, self).closeEvent(event)


class MagneticMove:
    def GetResources(self):
        return {'Pixmap': str(Path(__file__).with_name('WorkbenchMagneticMove.svg')),
                'MenuText': 'Magnetic Move', 'ToolTip': 'Select one solid, choose its corner and move with exact snaps'}
    def IsActive(self):
        return App.ActiveDocument is not None
    def Activated(self):
        try:
            part = selected_piece()
            if not _independent(part):
                raise ValueError('Choose an independent solid outside a Part or Body container.')
            for name in ('_workbench_magnetic_move_dialog', '_workbench_place_edit_dialog',
                         '_workbench_corner_dialog', '_workbench_rotate_dialog'):
                previous = getattr(Gui, name, None)
                if previous is not None:
                    previous.close()
            gui_doc = Gui.activeDocument()
            if gui_doc.getInEdit() is not None:
                gui_doc.resetEdit()
            dialog = MagneticMoveDialog(part)
            Gui._workbench_magnetic_move_dialog = dialog
            dialog.show()
        except Exception as error:
            QtWidgets.QMessageBox.information(Gui.getMainWindow(), 'Magnetic Move', str(error))


Gui.addCommand('DIY_MagneticMove', MagneticMove())
