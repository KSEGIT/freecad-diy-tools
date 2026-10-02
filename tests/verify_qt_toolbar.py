"""Real Qt widgets; only FreeCAD's native toolbar creation is simulated."""
from pathlib import Path
import sys, types, importlib.util, unittest
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD
from PySide import QtCore, QtWidgets, QtGui
application=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
class Params:
    def __init__(self): self.values={}; self.groups={}
    def GetString(self,k,d=''): return self.values.get(k,d)
    def SetString(self,k,v): self.values[k]=v
    def GetBool(self,k,d=False): return self.values.get(k,d)
    def SetBool(self,k,v): self.values[k]=v
    def GetGroup(self,k): return self.groups.setdefault(k,Params())
    def GetGroups(self): return list(self.groups)
class Window(QtWidgets.QMainWindow):
    workbenchActivated=QtCore.Signal(str)
class ToolbarTests(unittest.TestCase):
    def setUp(self):
        self.params={}; self.main=Window(); self.main.setProperty('eventLoop',True)
        self.main.resize(900,500); self.main.show()
        self.vendor=QtWidgets.QToolBar('Vendor',self.main); self.vendor.setObjectName('Vendor'); self.main.addToolBar(self.vendor)
        self.main.menuBar().setNativeMenuBar(False)
        self.menu=self.main.menuBar().addMenu('Tools'); self.menu.setObjectName('Std_ToolsMenu')
        self.edit=self.main.menuBar().addMenu('Edit'); self.edit.setObjectName('Std_EditMenu')
        self.command_actions={}; self.invoked=[]
        self.active='PartWorkbench'; self.reloads=0
        gui=types.ModuleType('FreeCADGui'); gui.getMainWindow=lambda:self.main
        gui.activeWorkbench=lambda:types.SimpleNamespace(reloadActive=self.reload)
        gui.Command=types.SimpleNamespace(get=lambda name:types.SimpleNamespace(getAction=lambda:self.command_actions.get(name,[])))
        self.old_app=sys.modules['FreeCAD']; self.old_gui=sys.modules.get('FreeCADGui')
        sys.modules['FreeCAD']=types.SimpleNamespace(ParamGet=self.param,Console=types.SimpleNamespace(PrintError=print))
        sys.modules['FreeCADGui']=gui
        spec=importlib.util.spec_from_file_location('toolbar_test',Path(__file__).resolve().parents[1]/'DIYWorkbenchTools'/'WorkbenchToolbarLayout.py')
        self.module=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.module)
    def param(self,path): return self.params.setdefault(path,Params())
    def reload(self):
        self.reloads+=1
        if self.active == 'NoneWorkbench': return
        self.toolbar=self.main.findChild(QtWidgets.QToolBar,'DIY tools')
        if self.toolbar is None:
            self.toolbar=QtWidgets.QToolBar('DIY tools',self.main); self.toolbar.setObjectName('DIY tools'); self.main.addToolBar(self.toolbar)
        for command in self.module.COMMANDS:
            if command not in self.command_actions:
                action=QtGui.QAction(command,self.main); action.setObjectName(command)
                action.triggered.connect(lambda checked=False,c=command:self.invoked.append(c))
                self.command_actions[command]=[action]
                self.toolbar.addAction(action)
        self.toolbar.show()
    def ready(self):
        self.assertTrue(hasattr(self.module,'ToolbarController'),'missing universal toolbar controller')
        self.controller=self.module.ToolbarController(self.main); self.controller.install(); application.processEvents()
    def tearDown(self):
        self.main.close(); self.main.deleteLater(); application.processEvents()
        sys.modules['FreeCAD']=self.old_app
        if self.old_gui is None: sys.modules.pop('FreeCADGui',None)
        else: sys.modules['FreeCADGui']=self.old_gui
    def test_registers_native_global_commands_without_vendor_changes(self):
        self.ready(); group=self.param(self.module.GLOBAL_PREFS).GetGroup(self.module.GROUP)
        self.assertEqual(group.GetString('Name'),'DIY tools'); self.assertTrue(group.GetBool('Active'))
        self.assertEqual(set(group.values)-{'Name','Active'},set(self.module.COMMANDS))
        self.assertEqual(self.reloads,1); self.assertTrue(self.main.toolBarBreak(self.toolbar))
        self.assertEqual(self.main.toolBarArea(self.vendor),QtCore.Qt.TopToolBarArea)
    def test_toggle_persists_user_choice_and_switch_does_not_reset_it(self):
        self.ready(); self.toolbar.toggleViewAction().trigger()
        self.assertFalse(self.param(self.module.PREFS).GetBool('Enabled',True))
        self.toolbar.show(); self.controller.workbench_activated('DraftWorkbench'); application.processEvents()
        self.assertFalse(self.toolbar.isVisible()); self.assertFalse(self.controller.toggle.isChecked())
        self.controller.toggle.trigger(); application.processEvents(); self.assertTrue(self.toolbar.isVisible())
        self.assertTrue(self.param(self.module.PREFS).GetBool('Enabled'))
    def test_disabled_restart_and_menu_recreation_are_supported(self):
        self.param(self.module.PREFS).SetBool('Enabled',False); self.ready()
        self.assertFalse(self.toolbar.isVisible())
        self.main.menuBar().removeAction(self.menu.menuAction()); self.menu.deleteLater(); application.processEvents()
        menu=self.main.menuBar().addMenu('Tools'); menu.setObjectName('Std_ToolsMenu')
        self.controller.workbench_activated('SketcherWorkbench'); application.processEvents()
        self.assertIn(self.controller.menu.menuAction(),menu.actions())
        self.controller.toggle.trigger(); self.assertTrue(self.toolbar.isVisible())
    def test_transient_workbench_hiding_does_not_disable_preference(self):
        self.ready(); self.toolbar.hide(); self.controller.workbench_activated('WoodworkingWorkbench'); application.processEvents()
        self.assertTrue(self.toolbar.isVisible()); self.assertTrue(self.param(self.module.PREFS).GetBool('Enabled',True))
    def test_late_native_restore_cannot_collapse_last_row(self):
        second=QtWidgets.QToolBar('Vendor second',self.main); second.setObjectName('Vendor second')
        self.main.addToolBar(second); self.main.insertToolBarBreak(second)
        self.ready()
        # Tux runs after plugin installation and can put DIY in an earlier row.
        def late_restore():
            self.main.removeToolBarBreak(self.toolbar)
            self.main.removeToolBar(self.toolbar)
            self.main.insertToolBar(self.vendor,self.toolbar)
        QtCore.QTimer.singleShot(500,late_restore)
        loop=QtCore.QEventLoop(); QtCore.QTimer.singleShot(700,loop.quit); loop.exec()
        self.assertTrue(self.main.toolBarBreak(self.toolbar))
        self.assertGreater(self.toolbar.geometry().y(),self.vendor.geometry().y())
        self.assertGreater(self.toolbar.geometry().y(),second.geometry().y())
    def test_initial_none_waits_for_native_workbench_then_shows_row(self):
        self.active='NoneWorkbench'; self.ready()
        self.assertIsNone(self.controller.toolbar)
        self.active='PartWorkbench'; self.reload()
        self.main.workbenchActivated.emit(self.active); application.processEvents()
        self.assertTrue(self.toolbar.isVisible()); self.assertTrue(self.main.toolBarBreak(self.toolbar))
        self.toolbar.hide(); self.active='NoneWorkbench'
        self.main.workbenchActivated.emit(self.active); application.processEvents()
        self.assertTrue(self.toolbar.isVisible())
    def test_move_rotate_share_toolbar_actions_with_edit_menu(self):
        self.ready()
        for command in ('DIY_MovePart','DIY_AutoMove','DIY_RotatePart','DIY_MagneticMove'):
            self.assertIn(command,self.module.COMMANDS)
            action=self.command_actions[command][0]
            self.assertIn(action,self.toolbar.actions())
            self.assertIn(action,self.edit.actions())
            action.trigger()
        self.assertEqual(self.invoked,['DIY_MovePart','DIY_AutoMove','DIY_RotatePart','DIY_MagneticMove'])
        self.controller.relocate()
        for command in ('DIY_MovePart','DIY_AutoMove','DIY_RotatePart','DIY_MagneticMove'):
            self.assertEqual(self.edit.actions().count(self.command_actions[command][0]),1)
    def test_auto_snap_button_is_checkable_and_restores_saved_state(self):
        self.ready()
        action=self.command_actions['DIY_MagneticMove'][0]
        self.assertTrue(action.isCheckable())
        self.assertTrue(action.isChecked())
        self.param(self.module.PREFS).SetBool('SnapEnabled',False)
        self.controller.relocate()
        self.assertFalse(action.isChecked())
        self.assertIn(action,self.edit.actions())
        self.main.workbenchActivated.emit('DraftWorkbench'); application.processEvents()
        self.assertFalse(action.isChecked())
    def test_edit_menu_recreation_preserves_move_rotate(self):
        self.ready()
        self.main.menuBar().removeAction(self.edit.menuAction()); self.edit.deleteLater()
        application.processEvents()
        menu=self.main.menuBar().addMenu('Edit'); menu.setObjectName('Std_EditMenu')
        self.main.workbenchActivated.emit('DraftWorkbench'); application.processEvents()
        for command in ('DIY_MovePart','DIY_AutoMove','DIY_RotatePart','DIY_MagneticMove'):
            self.assertIn(command,self.command_actions)
            self.assertIn(self.command_actions[command][0],menu.actions())
if __name__=='__main__': unittest.main()
