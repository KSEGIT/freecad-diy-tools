"""Standalone DIY tools workbench; install as DIYWorkbenchTools/InitGui.py."""
import importlib as _diy_importlib
from pathlib import Path as _DIYPath
import sys as _diy_sys

import FreeCAD as _DIYApp
import FreeCADGui as _DIYGui

# FreeCAD execs InitGui.py without defining __file__. Addon Manager may add
# either the workbench directory or its containing package to sys.path.
_diy_root = next((entry for entry in _diy_sys.path
                  if _DIYPath(entry).name == 'DIYWorkbenchTools'), None)
if _diy_root is None:
    _diy_root = next((str(_DIYPath(entry) / 'DIYWorkbenchTools')
                      for entry in _diy_sys.path
                      if (_DIYPath(entry) / 'DIYWorkbenchTools').is_dir()), None)
if _diy_root is None:
    if '__file__' in globals():
        _diy_root = str(_DIYPath(__file__).resolve().parent)
    else:
        _diy_root = str(_DIYPath(_DIYApp.getUserAppDataDir()) /
                        'Mod' / 'DIYWorkbenchTools')
_diy_root = str(_DIYPath(_diy_root).resolve())
if _diy_root in _diy_sys.path:
    _diy_sys.path.remove(_diy_root)
_diy_sys.path.insert(0, _diy_root)


class DIYWorkbenchToolsWorkbench(Workbench):
    MenuText = 'DIY tools'
    ToolTip = 'Add timber and plywood, edit cut sizes, and place solid pieces'
    Icon = str(_DIYPath(_diy_root) / 'WorkbenchParts.svg')

    def Initialize(self):
        # PartGui supplies the view providers for the solids these tools create.
        for module in ('PartGui', 'WorkbenchPartsCommand', 'WorkbenchPlacement',
                       'WorkbenchPlaceEdit'):
            _diy_importlib.import_module(module)
        commands = ['DIY_AddWorkbenchParts', 'DIY_PlaceEdit', 'DIY_JoinCorners',
                    'DIY_StandUpright', 'DIY_RotateX', 'DIY_RotateY', 'DIY_RotateZ']
        self.appendToolbar('DIY tools', commands)
        self.appendMenu(['DIY tools'], commands)

    def Activated(self):
        # Write persistent order now; place the toolbar after FreeCAD restores it.
        _diy_importlib.import_module('WorkbenchToolbarLayout').ensure_row()

    def GetClassName(self):
        return 'Gui::PythonWorkbench'


_DIYGui.addWorkbench(DIYWorkbenchToolsWorkbench())
