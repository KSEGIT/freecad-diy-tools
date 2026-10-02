"""Universal DIY toolbar using FreeCAD's native global custom toolbar support.

FreeCAD's Workbench::setupCustomToolbars reads Global/Toolbar on each switch.
A zero-delay relocation follows synchronous workbench layout restoration;
one extra startup relocation follows Tux's initial 500 ms restore timer.
"""
import importlib
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui

NAME = 'DIY tools'
GROUP = 'Custom_DIYWorkbenchTools'
PREFS = 'User parameter:BaseApp/Preferences/DIYWorkbenchTools'
GLOBAL_PREFS = 'User parameter:BaseApp/Workbench/Global/Toolbar'
VISIBILITY_PREFS = 'User parameter:BaseApp/MainWindow/Toolbars'
COMMANDS = ('DIY_AddWorkbenchParts', 'DIY_MovePart', 'DIY_RotatePart', 'DIY_MagneticMove',
            'DIY_PlaceEdit', 'DIY_JoinCorners',
            'DIY_StandUpright', 'DIY_RotateX', 'DIY_RotateY', 'DIY_RotateZ')
_controller = None
_start_attempts = 0


class ToolbarController:
    def __init__(self, main):
        self.main = main
        self.toolbar = None
        self.prefs = App.ParamGet(PREFS)
        self.menu = QtWidgets.QMenu('DIY toolbar', main)
        self.menu.setObjectName('DIYToolbarMenu')
        # Hold menu action wrappers: FreeCAD's PySide6 bridge can give them
        # Python ownership when returned by menuBar().actions().
        self.menu_action = self.menu.menuAction()
        self.tools_action = None
        self.main_menu_actions = []
        self.edit_actions = []
        self.toggle = QtGui.QAction('Show DIY tools', main)
        self.toggle.setCheckable(True)
        self.toggle.setChecked(self.enabled())
        self.toggle.triggered.connect(self.set_enabled)
        self.menu.addAction(self.toggle)
        self.restore_timer = QtCore.QTimer(main)
        self.restore_timer.setSingleShot(True)
        self.restore_timer.timeout.connect(self.relocate)
        self.startup_timer = QtCore.QTimer(main)
        self.startup_timer.setSingleShot(True)
        self.startup_timer.timeout.connect(self.relocate)

    def enabled(self):
        return self.prefs.GetBool('Enabled', True)

    def install(self):
        group = App.ParamGet(GLOBAL_PREFS).GetGroup(GROUP)
        group.SetString('Name', NAME)
        # Keep commands registered even when hidden, so View > Toolbars can
        # re-enable them. The separate Enabled setting controls visibility.
        group.SetBool('Active', True)
        for command in COMMANDS:
            group.SetString(command, 'FreeCAD')
        App.ParamGet(VISIBILITY_PREFS).SetBool(NAME, self.enabled())
        self.main.workbenchActivated.connect(self.workbench_activated)
        # Reload this active workbench through its public API; FreeCAD creates
        # the native command actions, including IsActive updates and icons.
        active = Gui.activeWorkbench()
        if active is not None:
            active.reloadActive()
        self.relocate()
        self.startup_timer.start(600)

    def set_enabled(self, enabled):
        self.prefs.SetBool('Enabled', bool(enabled))
        App.ParamGet(VISIBILITY_PREFS).SetBool(NAME, bool(enabled))
        self.toggle.setChecked(bool(enabled))
        self.relocate()

    def workbench_activated(self, *args):
        # Do not persist visibilityChanged: FreeCAD temporarily hides bars
        # during a workbench transition. Only explicit user toggles persist.
        self.restore_timer.start(0)

    def restore_menu(self):
        self.main_menu_actions = self.main.menuBar().actions()
        for action in self.main_menu_actions:
            tools = action.menu()
            if tools and (tools.objectName() == 'Std_ToolsMenu'
                          or action.objectName() == 'Std_ToolsMenu'
                          or action.text().replace('&', '') == 'Tools'):
                self.tools_action = action
                if self.menu_action not in tools.actions():
                    tools.addMenu(self.menu)
            if tools and (tools.objectName() == 'Std_EditMenu'
                          or action.objectName() == 'Std_EditMenu'
                          or action.text().replace('&', '') == 'Edit'):
                # Reuse the native command actions so availability, tooltips,
                # icons and shortcuts match the toolbar in every workbench.
                self.edit_actions = []
                for command_name in ('DIY_MovePart', 'DIY_RotatePart', 'DIY_MagneticMove'):
                    command = Gui.Command.get(command_name)
                    if command is None:
                        continue
                    for command_action in command.getAction():
                        self.edit_actions.append(command_action)
                        if command_action not in tools.actions():
                            tools.addAction(command_action)

    def relocate(self):
        self.restore_menu()
        toolbar = self.main.findChild(QtWidgets.QToolBar, NAME)
        if toolbar is None:
            return
        self.toolbar = toolbar
        toggle = toolbar.toggleViewAction()
        if not toolbar.property('DIYToggleConnected'):
            toggle.triggered.connect(self.set_enabled)
            toolbar.setProperty('DIYToggleConnected', True)
        # A fresh native toolbar hides its menu action on NoneWorkbench.
        # This extension owns its visibility on every workbench.
        toggle.setVisible(True)
        self.main.removeToolBarBreak(toolbar)
        self.main.removeToolBar(toolbar)
        self.main.addToolBar(QtCore.Qt.TopToolBarArea, toolbar)
        self.main.insertToolBarBreak(toolbar)
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        toolbar.setVisible(self.enabled())
        self.toggle.setChecked(self.enabled())


def start():
    """Start once after FreeCAD enters its GUI event loop (bounded retry)."""
    global _controller, _start_attempts
    if _controller is not None:
        _controller.relocate()
        return
    main = Gui.getMainWindow()
    if main is None or not main.property('eventLoop'):
        _start_attempts += 1
        if _start_attempts <= 40:
            QtCore.QTimer.singleShot(500, start)
        else:
            App.Console.PrintError('DIY tools: GUI startup timed out. Restart FreeCAD or call WorkbenchToolbarLayout.start().\n')
        return
    for module in ('PartGui', 'WorkbenchPartsCommand', 'WorkbenchPlacement',
                   'WorkbenchPlaceEdit', 'WorkbenchMoveRotate', 'WorkbenchMagneticMove'):
        importlib.import_module(module)
    _controller = ToolbarController(main)
    _controller.install()
