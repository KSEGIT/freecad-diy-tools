"""Modeless magnetic translation with an unpickable Coin preview.

View bindings verified in official FreeCAD src/Gui/View3DPy.cpp at the
installed 1.1.3 commit 145529fe741292ff0b3977a01195bf0247425794.
"""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from pivy import coin
from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui
from WorkbenchPlacement import selected_piece
from WorkbenchMagneticGeometry import (
    constrained_point, translated_placement,
)

from WorkbenchConnectionSnap import connection_snap


def snap_enabled():
    return App.ParamGet("User parameter:BaseApp/Preferences/DIYWorkbenchTools").GetBool("SnapEnabled", True)


def set_snap_enabled(enabled):
    App.ParamGet("User parameter:BaseApp/Preferences/DIYWorkbenchTools").SetBool("SnapEnabled", bool(enabled))
    # Installed Draft uses Command.get(...).getAction() for shared Qt actions.
    if hasattr(Gui, 'Command'):
        command = Gui.Command.get('DIY_MagneticMove')
        if command is not None:
            actions = command.getAction()
            Gui._workbench_snap_actions = actions
            for action in actions:
                action.setCheckable(True)
                action.setChecked(bool(enabled))
    dialog = getattr(Gui, "_workbench_magnetic_move_dialog", None)
    if dialog is not None and not dialog.closed:
        blocked = dialog.snap_button.blockSignals(True)
        dialog.snap_button.setChecked(bool(enabled))
        dialog.snap_button.blockSignals(blocked)
        dialog.connection = None
        if dialog.last_position is not None:
            dialog.move(dialog.last_position)


def toggle_snap():
    set_snap_enabled(not snap_enabled())


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
        self.source_shape = part.Shape.copy()
        self.source = App.Vector(self.source_shape.CenterOfMass)
        self.destination = App.Vector(self.source)
        self.connection = None
        self.last_position = None
        self.axis = None
        self.closed = False
        self.callback = None
        self.preview_root = None
        self.cache = {}
        self.left_down = False
        self.setWindowTitle('Auto Move — ' + part.Label[:32])
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setMinimumWidth(300)
        self.setMaximumWidth(380)
        layout = QtWidgets.QVBoxLayout(self)
        self.message = QtWidgets.QLabel()
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
        self.snap_button = QtWidgets.QCheckBox('Auto snap (S)')
        self.snap_button.setChecked(snap_enabled())
        self.snap_button.toggled.connect(set_snap_enabled)
        layout.addWidget(self.snap_button)
        cancel = QtWidgets.QPushButton('Cancel'); cancel.clicked.connect(self.close); layout.addWidget(cancel)
        self.timer = QtCore.QTimer(self); self.timer.setInterval(100)
        self.timer.timeout.connect(self.check_context)
        try:
            self.make_preview()
            self.preview(self.source, "Free move")
            self.callback = self.view.addEventCallbackPivy(coin.SoEvent.getClassTypeId(), self.handle_event)
            Gui.Selection.clearSelection()
            Gui._workbench_magnetic_move_dialog = self
            self.timer.start()
            parent = Gui.getMainWindow()
            if parent is not None:
                edge = parent.mapToGlobal(parent.rect().topRight())
                self.move_window(edge.x() - 390, edge.y() + 70)
        except Exception:
            self.cleanup()
            raise

    def move_window(self, x, y):
        QtWidgets.QDialog.move(self, x, y)

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
        """Snapshot independent visible solids; refresh when shape or placement changes."""
        result = []; present = set(); self.target_objects = {}
        for obj in self.doc.Objects:
            if obj is self.part or not _independent(obj) or not _visible(obj):
                continue
            present.add(obj.Name)
            key = (obj.Shape.hashCode(), str(obj.Placement), obj.Label)
            cached = self.cache.get(obj.Name)
            if cached is None or cached[0] != key:
                cached = (key, obj.Shape.copy()); self.cache[obj.Name] = cached
            result.append((obj.Label, cached[1])); self.target_objects[id(cached[1])] = obj
        for name in list(self.cache):
            if name not in present:
                del self.cache[name]
        return result

    def capture_distance(self, position):
        """Include the two-pixel retention margin without allowing distant depth jumps."""
        a = self.point_on_plane(position)
        b = self.point_on_plane((position[0] + 20, position[1]))
        c = self.point_on_plane((position[0], position[1] + 20))
        return max(0.001, min(50., max((a-b).Length, (a-c).Length)))

    def find_connection(self, raw_delta, position):
        targets = self.targets()
        previous = self.connection
        while targets:
            snap = connection_snap(self.source_shape, targets, raw_delta,
                                   self.view.getPointOnScreen, world_tolerance=self.capture_distance(position),
                                   axis=self.axis, previous=previous)
            if snap is None:
                return None
            # Face centres can project onto another face of the same solid.
            # Reject occlusion by a different solid; silhouette rounding may miss.
            pixel = self.view.getPointOnScreen(snap['target'])
            info = self.view.getObjectInfo(tuple(int(v) for v in pixel))
            index = snap['key'][0]
            target_obj = self.target_objects[id(targets[index][1])]
            if (not info or (info.get('Document') == self.docname
                             and info.get('Object') == target_obj.Name
                             and 'ParentObject' not in info)):
                return snap
            targets.pop(index)
            previous = None
        return None

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
        if not self.closed and not self.valid_context():
            self.close()
        if self.closed:
            return
        self.last_position = position
        point = self.axis_point(position, self.point_on_plane(position))
        # Preserve native navigation: modifiers are handled before reaching here.
        snap = self.find_connection(point - self.source, position) if snap_enabled() else None
        self.connection = snap
        if snap is not None:
            self.preview(self.source + snap['delta'], snap['label'][:32] + ' — ' + snap['kind'])
        else:
            self.preview(point, 'Free move' if self.axis is None else self.axis + ' axis')

    def preview(self, destination, label):
        self.destination = App.Vector(destination)
        delta = self.destination - self.source
        self.translation.translation.setValue(delta.x, delta.y, delta.z)
        self.ghost_switch.whichChild = coin.SO_SWITCH_ALL
        self.marker_coords.point.setValue(tuple(self.destination)); self.marker.numPoints = 1
        # Three world-axis steps show the delta as well as the direct travel line.
        a = self.source; b = a + App.Vector(delta.x, 0, 0); c = b + App.Vector(0, delta.y, 0)
        points = [tuple(a), tuple(b), tuple(c), tuple(self.destination), tuple(a), tuple(self.destination)]
        self.guide_coords.point.setNum(len(points))
        self.guide_coords.point.setValues(0, len(points), points)
        self.lines.numVertices.setNum(2)
        self.lines.numVertices.setValues(0, 2, [4, 2])
        if self.connection is not None:
            contact = self.connection['source']; target = self.connection['target']
            points.extend([tuple(contact), tuple(target)])
            self.guide_coords.point.setValues(0, len(points), points)
            self.lines.numVertices.setValues(0, 3, [4, 2, 2])
            self.marker_coords.point.setValue(tuple(target))
        self.message.setText('{}\nΔ X {:.2f}  Y {:.2f}  Z {:.2f} mm\nDistance {:.2f} mm\nClick to place. X / Y / Z lock; S snap; Esc cancels.'.format(
            label, delta.x, delta.y, delta.z, delta.Length))

    def click(self, position):
        if not self.closed:
            self.move(position)
            self.commit()

    def set_axis(self, axis, toggle=True):
        if toggle and axis == self.axis:
            axis = None
        self.axis = axis
        self.connection = None
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
        self.connection = None
        self.preview(self.source + axis * self.distance.value(), self.axis + ' exact distance')
        self.commit()

    def commit(self):
        if not self.valid_context():
            self.close(); return
        if self.source is None or self.destination is None:
            return
        self.doc.openTransaction('Move DIY part')
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
                    elif key == coin.SoKeyboardEvent.S:
                        callback.setHandled(); toggle_snap()
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
        elif event.key() == QtCore.Qt.Key_S:
            toggle_snap(); event.accept()
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
                'MenuText': 'Auto snap', 'ToolTip': 'Toggle automatic face, end and corner connections (S)',
                'Checkable': snap_enabled(), 'CmdType': 'NoTransaction'}
    def IsActive(self):
        return True
    def Activated(self, status=0):
        toggle_snap()


def start_move():
    try:
        previous = getattr(Gui, '_workbench_magnetic_move_dialog', None)
        prior_part = None
        if previous is not None:
            # Starting a session clears selection. Reentry can reuse its
            # source only while the previous context is still valid.
            if not previous.closed and previous.valid_context():
                prior_part = previous.part
            previous.close()
        part = (prior_part if not Gui.Selection.getSelection() and prior_part is not None
                else selected_piece())
        if not _independent(part):
            raise ValueError('Choose an independent solid outside a Part or Body container.')
        for name in ('_workbench_place_edit_dialog',
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
        QtWidgets.QMessageBox.information(Gui.getMainWindow(), 'Move part', str(error))

Gui.addCommand('DIY_MagneticMove', MagneticMove())
