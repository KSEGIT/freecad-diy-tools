"""Independent DIY workbench startup tests with native GUI boundaries simulated."""
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'DIYWorkbenchTools' / 'InitGui.py'

class Workbench:
    def __init__(self):
        self.toolbars, self.menus = [], []
    def appendToolbar(self, name, commands):
        self.toolbars.append((name, list(commands)))
    def appendMenu(self, path, commands):
        self.menus.append((path, list(commands)))

class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.registry, self.rows = {}, []
        self.gui = types.SimpleNamespace(addWorkbench=self.add_workbench)
        self.app = types.SimpleNamespace(getUserAppDataDir=lambda: '/Users/example/FreeCAD/')
        self.modules = {
            'FreeCAD': self.app, 'FreeCADGui': self.gui,
            'PartGui': types.SimpleNamespace(),
            'WorkbenchPartsCommand': types.SimpleNamespace(),
            'WorkbenchPlacement': types.SimpleNamespace(),
            'WorkbenchPlaceEdit': types.SimpleNamespace(),
            'WorkbenchToolbarLayout': types.SimpleNamespace(ensure_row=lambda: self.rows.append('row')),
        }
        self.patch = patch.dict(sys.modules, self.modules)
        self.patch.start()
        self.path_before = sys.path[:]
        # Isolate path scenarios from discovery's real repository working directory.
        sys.path[:] = [entry for entry in sys.path
                       if Path(entry).name != 'DIYWorkbenchTools'
                       and not (Path(entry) / 'DIYWorkbenchTools').is_dir()]
    def tearDown(self):
        self.patch.stop()
        sys.path[:] = self.path_before
    def add_workbench(self, wb):
        self.registry[type(wb).__name__] = wb
    def load(self, with_file=True):
        scope = {'Workbench': Workbench, '__name__': '__main__'}
        if with_file:
            scope['__file__'] = str(SOURCE)
        exec(compile(SOURCE.read_text(), str(SOURCE), 'exec'), scope)
        self.assertIn('DIYWorkbenchToolsWorkbench', self.registry)
        return self.registry['DIYWorkbenchToolsWorkbench']
    def test_registers_independent_dropdown_without_woodworking(self):
        wb = self.load()
        self.assertEqual(wb.MenuText, 'DIY tools')
        self.assertEqual(wb.GetClassName(), 'Gui::PythonWorkbench')
        self.assertEqual(wb.toolbars, [])
    def test_initialize_creates_own_toolbar_and_menu_with_seven_commands(self):
        wb = self.load()
        wb.Initialize()
        commands = ['DIY_AddWorkbenchParts', 'DIY_PlaceEdit', 'DIY_JoinCorners',
                    'DIY_StandUpright', 'DIY_RotateX', 'DIY_RotateY', 'DIY_RotateZ']
        self.assertEqual(wb.toolbars, [('DIY tools', commands)])
        self.assertEqual(wb.menus, [(['DIY tools'], commands)])
    def test_activation_enforces_own_layout_each_time(self):
        wb = self.load()
        wb.Initialize()
        wb.Activated()
        wb.Activated()
        self.assertEqual(self.rows, ['row', 'row'])
    def test_native_initgui_without_file_uses_addon_path(self):
        with tempfile.TemporaryDirectory() as folder:
            addon = Path(folder).resolve() / 'DIYWorkbenchTools'
            addon.mkdir()
            sys.path.append(str(addon))
            self.load(with_file=False)
            self.assertEqual(sys.path[0], str(addon))
    def test_native_initgui_without_path_uses_user_addon_directory(self):
        self.load(with_file=False)
        self.assertEqual(sys.path[0], '/Users/example/FreeCAD/Mod/DIYWorkbenchTools')
    def test_nested_addon_manager_workbench_directory_is_used(self):
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder).resolve()
            (package / 'DIYWorkbenchTools').mkdir()
            sys.path.append(str(package))
            self.load(with_file=False)
            self.assertEqual(sys.path[0], str(package / 'DIYWorkbenchTools'))

if __name__ == '__main__':
    unittest.main()
