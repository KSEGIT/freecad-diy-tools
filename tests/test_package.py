"""FreeCAD 1.1 package GUI loader must find the universal extension."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = {'p': 'https://wiki.freecad.org/Package_Metadata'}


class PackageTests(unittest.TestCase):
    def test_metadata_routes_gui_loading_without_registering_workbench(self):
        package = ET.parse(ROOT / 'package.xml').getroot()
        contents = package.findall('p:content/p:workbench', NS)
        self.assertEqual(len(contents), 1)
        entry = contents[0]
        directory = entry.findtext('p:subdirectory', namespaces=NS)
        init = ROOT / directory / 'InitGui.py'
        self.assertTrue(init.is_file())
        self.assertFalse(entry.findtext('p:classname', namespaces=NS))
        source = init.read_text()
        self.assertNotIn('addWorkbench', source)
        self.assertIn("import_module('WorkbenchToolbarLayout').start()", source)
        # FreeCAD 1.1 processes metadata instead of root InitGui, so the
        # content entry above must not be replaced by an empty <content/>.
        self.assertEqual(entry.findtext('p:freecadmin', namespaces=NS), '1.1.0')


if __name__ == '__main__':
    unittest.main()
