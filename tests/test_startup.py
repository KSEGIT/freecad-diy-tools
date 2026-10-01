"""InitGui loads a global extension, never a workbench or vendor module."""
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
SOURCE = Path(__file__).resolve().parents[1] / 'DIYWorkbenchTools' / 'InitGui.py'
class StartupTests(unittest.TestCase):
    def setUp(self):
        self.calls=[]
        self.before=sys.path[:]
        self.modules={'FreeCAD':types.SimpleNamespace(getUserAppDataDir=lambda:'/example/FreeCAD/'),
                      'FreeCADGui':types.SimpleNamespace(addWorkbench=lambda wb:self.calls.append('workbench')),
                      'WorkbenchToolbarLayout':types.SimpleNamespace(start=lambda:self.calls.append('start'))}
        self.patch=patch.dict(sys.modules,self.modules); self.patch.start()
        sys.path[:]=[p for p in sys.path if Path(p).name!='DIYWorkbenchTools' and not (Path(p)/'DIYWorkbenchTools').is_dir()]
    def tearDown(self):
        self.patch.stop(); sys.path[:]=self.before
    def load(self,with_file=True,separate_locals=False):
        scope={'__name__':'__main__','Workbench':object}
        if with_file: scope['__file__']=str(SOURCE)
        exec(compile(SOURCE.read_text(),str(SOURCE),'exec'),scope,{} if separate_locals else scope)
    def test_starts_extension_without_registering_workbench(self):
        self.load(); self.assertEqual(self.calls,['start'])
    def test_native_no_file_uses_module_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'DIYWorkbenchTools'; path.mkdir(); sys.path.append(str(path))
            self.load(False); self.assertEqual(sys.path[0],str(path.resolve()))
    def test_native_loader_separate_globals_and_locals(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'DIYWorkbenchTools'; path.mkdir(); sys.path.append(str(path))
            self.load(False,separate_locals=True)
            self.assertEqual(self.calls,['start'])
            self.assertEqual(sys.path[0],str(path.resolve()))
    def test_native_loader_separate_scopes_with_package_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'DIYWorkbenchTools'; path.mkdir(); sys.path.append(folder)
            self.load(False,separate_locals=True)
            self.assertEqual(self.calls,['start'])
            self.assertEqual(sys.path[0],str(path.resolve()))
    def test_native_no_file_falls_back_to_user_mod(self):
        self.load(False); self.assertEqual(sys.path[0],'/example/FreeCAD/Mod/DIYWorkbenchTools')
    def test_package_directory_is_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'DIYWorkbenchTools').mkdir(); sys.path.append(folder)
            self.load(False); self.assertEqual(sys.path[0],str(Path(folder).resolve()/'DIYWorkbenchTools'))
if __name__=='__main__': unittest.main()
