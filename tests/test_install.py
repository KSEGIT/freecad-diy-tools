import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def test_vendor_files_remain_untouched_and_reinstall_is_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vendor = root / 'woodworking'
            vendor.mkdir()
            init = vendor / 'InitGui.py'
            init.write_text('original vendor file')
            target = installer.install(root)
            self.assertEqual(init.read_text(), 'original vendor file')
            self.assertTrue((target / 'InitGui.py').is_file())
            self.assertTrue((target / 'Add_Workbench_Parts.FCMacro').is_file())
            self.assertEqual(target.name, 'DIYWorkbenchTools')
            installer.install(root)
            self.assertEqual(init.read_text(), 'original vendor file')
            source = (target / 'WorkbenchPartsCommand.py').read_text()
            self.assertIn("Path(__file__).with_name('Add_Workbench_Parts.FCMacro')", source)
            self.assertNotIn('/Users/admin/', source)
