"""Separate movement and rotation commands for independent solid parts."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui
from WorkbenchPlacement import selected_piece
from WorkbenchPlaceEdit import AXES, rotated_placement


def close_editor():
    previous = getattr(Gui, '_workbench_place_edit_dialog', None)
    if previous is not None:
        previous.close()


def warning(error):
    QtWidgets.QMessageBox.warning(Gui.getMainWindow(), 'DIY move / rotate', str(error))


class MovePart:
    def GetResources(self):
        return {'Pixmap': str(Path(__file__).with_name('WorkbenchMove.svg')),
                'MenuText': 'Move part',
                'ToolTip': 'Select one solid part, then move it with the 3D arrows'}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            part = selected_piece()
            if App.ActiveDocument is not part.Document:
                raise ValueError('Activate the part document first.')
            close_editor()
            moving = getattr(Gui, '_workbench_magnetic_move_dialog', None)
            if moving is not None:
                moving.close()
            previous = getattr(Gui, '_workbench_rotate_dialog', None)
            if previous is not None:
                previous.close()
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(part)
            preferences = App.ParamGet('User parameter:BaseApp/History/Dragger')
            # Defaults apply only when absent; preserve the user's chosen steps.
            preferences.SetFloat('LastRotationIncrement', preferences.GetFloat('LastRotationIncrement', 90))
            preferences.SetFloat('LastTranslationIncrement', preferences.GetFloat('LastTranslationIncrement', 1))
            Gui.runCommand('Std_TransformManip', 0)
        except Exception as error:
            warning(error)


class AutoMove:
    def GetResources(self):
        return {'Pixmap': str(Path(__file__).with_name('WorkbenchAutoMove.svg')),
                'MenuText': 'Auto Move',
                'ToolTip': 'Move a whole part with the cursor and automatic connections'}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        from WorkbenchMagneticMove import start_move
        start_move()


class RotateDialog(QtWidgets.QDialog):
    def __init__(self, part):
        super(RotateDialog, self).__init__(Gui.getMainWindow())
        self.doc_name = part.Document.Name
        self.part_name = part.Name
        self.part = part
        self.setWindowTitle('Rotate part — ' + part.Label)
        self.setMinimumWidth(330)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel('Rotate around the part centre. Axes are global.'))
        form = QtWidgets.QFormLayout()
        self.axis = QtWidgets.QComboBox()
        self.axis.addItems(['X', 'Y', 'Z'])
        self.angle = QtWidgets.QDoubleSpinBox()
        self.angle.setRange(-36000, 36000)
        self.angle.setDecimals(2)
        self.angle.setSuffix('°')
        self.angle.setValue(90)
        form.addRow('Axis', self.axis)
        form.addRow('Angle', self.angle)
        layout.addLayout(form)
        buttons = QtWidgets.QHBoxLayout()
        apply_button = QtWidgets.QPushButton('Apply rotation')
        apply_button.clicked.connect(self.rotate)
        buttons.addWidget(apply_button)
        close_button = QtWidgets.QPushButton('Close')
        close_button.clicked.connect(self.close)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        self.status = QtWidgets.QLabel('Use Undo to reverse each rotation.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

    def rotate(self):
        try:
            doc = App.listDocuments().get(self.doc_name)
            if doc is None or doc.getObject(self.part_name) is not self.part:
                raise ValueError('This part is no longer available. Close this window and select a part again.')
            if App.ActiveDocument is not doc:
                raise ValueError('Activate the part document first.')
            rotation = App.Rotation(AXES[self.axis.currentIndex()], self.angle.value())
            placement = rotated_placement(self.part.Placement, rotation, self.part.Shape.CenterOfMass)
            doc.openTransaction('Rotate DIY part')
            try:
                self.part.Placement = placement
                doc.recompute()
                doc.commitTransaction()
            except Exception:
                doc.abortTransaction()
                raise
            self.status.setText('Rotation applied. Use Undo to reverse it.')
        except Exception as error:
            self.status.setText(str(error))

    def closeEvent(self, event):
        if getattr(Gui, '_workbench_rotate_dialog', None) is self:
            Gui._workbench_rotate_dialog = None
        super(RotateDialog, self).closeEvent(event)


class RotatePart:
    def GetResources(self):
        return {'Pixmap': str(Path(__file__).with_name('WorkbenchRotate.svg')),
                'MenuText': 'Rotate part',
                'ToolTip': 'Rotate one solid part around its centre by a chosen angle'}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            part = selected_piece()
            if App.ActiveDocument is not part.Document:
                raise ValueError('Activate the part document first.')
            close_editor()
            moving = getattr(Gui, '_workbench_magnetic_move_dialog', None)
            if moving is not None:
                moving.close()
            previous = getattr(Gui, '_workbench_rotate_dialog', None)
            if previous is not None:
                previous.close()
            Gui._workbench_rotate_dialog = RotateDialog(part)
            Gui._workbench_rotate_dialog.show()
        except Exception as error:
            warning(error)


Gui.addCommand('DIY_MovePart', MovePart())
Gui.addCommand('DIY_AutoMove', AutoMove())
Gui.addCommand('DIY_RotatePart', RotatePart())
