"""FreeCAD command for the local workbench parts macro."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui

MACRO_PATH = Path(__file__).with_name('Add_Workbench_Parts.FCMacro')
ICON_PATH = Path(__file__).with_name('WorkbenchParts.svg')


class AddWorkbenchParts:
    def GetResources(self):
        return {'Pixmap': str(ICON_PATH),
                'MenuText': 'Add timber / plywood',
                'ToolTip': 'Add a timber or plywood piece by cut dimensions'}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            code = compile(MACRO_PATH.read_text(), str(MACRO_PATH), 'exec')
            scope = {'__name__': '__main__', '__file__': str(MACRO_PATH)}
            exec(code, scope, scope)
        except Exception as error:
            App.Console.PrintError('Add timber / plywood: {}\n'.format(error))
            from PySide import QtGui
            try:
                from PySide import QtWidgets
            except ImportError:
                QtWidgets = QtGui
            QtWidgets.QMessageBox.critical(Gui.getMainWindow(), 'Add timber / plywood', str(error))


Gui.addCommand('DIY_AddWorkbenchParts', AddWorkbenchParts())
