"""Universal DIY toolbar extension; no workbench registration or vendor edits."""
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


_diy_importlib.import_module('WorkbenchToolbarLayout').start()
