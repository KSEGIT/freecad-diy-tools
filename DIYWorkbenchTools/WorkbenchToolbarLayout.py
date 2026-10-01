"""Keep DIY tools in their own row, including FreeCAD's persistent restore."""
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui

NAME = 'DIY tools'
PREFS = 'User parameter:Tux/PersistentToolbars/User/DIYWorkbenchToolsWorkbench'


def separate_row_order(order, name=NAME):
    items = [item for item in order.split(',') if item and item != name]
    while items and items[-1] == 'Break':
        items.pop()
    return ','.join(items + (['Break'] if items else []) + [name])


def remember_row(name=NAME):
    prefs = App.ParamGet(PREFS)
    top = prefs.GetString('Top')
    if top:
        prefs.SetString('Top', separate_row_order(top, name))
        prefs.SetBool('Saved', True)
    # A previously docked left/right/bottom DIY toolbar must not be restored there.
    for area in ('Left', 'Right', 'Bottom'):
        value = prefs.GetString(area)
        if name in value.split(','):
            items = [item for item in value.split(',') if item and item != name]
            while items and items[-1] == 'Break':
                items.pop()
            prefs.SetString(area, ','.join(items))


def place_toolbar():
    main = Gui.getMainWindow()
    for toolbar in main.findChildren(QtWidgets.QToolBar):
        if toolbar.windowTitle() == NAME or toolbar.objectName() == NAME:
            remember_row(toolbar.objectName() or NAME)
            main.removeToolBarBreak(toolbar)
            main.removeToolBar(toolbar)
            main.addToolBar(QtCore.Qt.TopToolBarArea, toolbar)
            main.insertToolBarBreak(toolbar)
            toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
            toolbar.show()
            return
    main.statusBar().showMessage('Enable DIY tools under View > Toolbars.', 10000)


def ensure_row():
    # FreeCAD's persistent toolbar module restores on a 500 ms startup timer.
    # Update its source settings before restore, not just the temporary Qt layout.
    remember_row()
    QtCore.QTimer.singleShot(0, place_toolbar)
